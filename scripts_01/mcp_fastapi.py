#!/usr/bin/env python3
"""
mcp_fastapi.py — FastAPI wrapper for Buffy MCP Server.

Exposes MCP Streamable HTTP protocol via FastAPI + uvicorn.
Supports Cloudflare Tunnel for public HTTPS access.

Protocol: MCP 2025-03-26 Streamable HTTP
  - POST /mcp: JSON-RPC requests → application/json or 202 Accepted
  - GET  /mcp: SSE notification stream (text/event-stream)
  - DELETE /mcp: session termination (204 No Content)

REST (без MCP-протокола):
  - POST /policy/override: User-Choice Override (правило 11, promt37)
    body: {"message": "use deepseek instead of claude for coding",
           "capability": "research" (опц.), "dry_run": true (опц.)]
  - GET  /policy/status: текущие предпочтения из policies.json (правило 11)

Usage:
    python scripts_01/mcp_fastapi.py                         # localhost:8765
    python scripts_01/mcp_fastapi.py --port 8000             # custom port
    python scripts_01/mcp_fastapi.py --tunnel                # + Cloudflare Tunnel
    python scripts_01/mcp_fastapi.py --tunnel --port 8000    # custom port + tunnel

    uvicorn scripts.mcp_fastapi:app --host 0.0.0.0 --port 8765

Claude Desktop config (Streamable HTTP):
    {
      "mcpServers": {
        "buffy": {
          "url": "https://YOUR-TUNNEL.trycloudflare.com/mcp",
          "transport": "streamable-http"
        }
      }
    }
"""

from __future__ import annotations

import asyncio
import hmac
import json
import os
import re
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

from scripts_01.mcp_server import (
    BuffyMcpServer,
    PROTOCOL_VERSION,
    PARSE_ERROR,
    INVALID_REQUEST,
    rpc_error,
)
from scripts_01 import task_manager  # Meeting Tasks REST (042_06 Phase E)

try:
    from fastapi import Depends, FastAPI, HTTPException, Request, Response
    from fastapi.responses import JSONResponse, StreamingResponse

    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

try:
    import hvac

    HAS_HVAC = True
except ImportError:
    HAS_HVAC = False


# ═══════════════════════════════════════════════════════════════
# Async Session Management
# ═══════════════════════════════════════════════════════════════


@dataclass
class McpAsyncSession:
    """MCP session with asyncio.Queue for async SSE streaming."""

    session_id: str
    notification_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class McpAsyncSessionManager:
    """Async session manager for FastAPI transport.

    Uses asyncio.Lock and asyncio.Queue (not threading.Lock / queue.Queue)
    to be compatible with uvicorn's event loop.
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, McpAsyncSession] = {}
        self._lock = asyncio.Lock()

    async def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        async with self._lock:
            self._sessions[session_id] = McpAsyncSession(session_id=session_id)
        return session_id

    async def get_session(self, session_id: str) -> Optional[McpAsyncSession]:
        async with self._lock:
            return self._sessions.get(session_id)

    async def delete_session(self, session_id: str) -> bool:
        async with self._lock:
            session = self._sessions.pop(session_id, None)
            if session:
                session.active = False
                return True
            return False

    async def push_notification(self, session_id: str, message: str) -> bool:
        session = await self.get_session(session_id)
        if session and session.active:
            await session.notification_queue.put(message)
            return True
        return False

    async def count(self) -> int:
        async with self._lock:
            return len(self._sessions)


# ═══════════════════════════════════════════════════════════════
# FastAPI Application
# ═══════════════════════════════════════════════════════════════

if HAS_FASTAPI:
    app = FastAPI(
        title="Buffy MCP Server",
        description="Model Context Protocol — Streamable HTTP (MCP 2025-03-26)",
        version="1.0.0",
    )

    _server: Optional[BuffyMcpServer] = None
    _sessions: Optional[McpAsyncSessionManager] = None
    _metrics: Optional[Any] = None  # MetricsEngine lazy init
    _policy_engine: Optional[Any] = None  # PolicyEngine lazy init (правило 11)

    @app.on_event("startup")
    async def _startup() -> None:
        global _server, _sessions, _metrics, _policy_engine
        _server = BuffyMcpServer()
        _sessions = McpAsyncSessionManager()
        # MetricsEngine инициализируется лениво (может не быть БД)
        _metrics = None
        _policy_engine = None
        print(
            f"🚀 Buffy MCP FastAPI server started\n"
            f"   Protocol: {PROTOCOL_VERSION}\n"
            f"   Tools: {len(_server._tools)} | "
            f"Resources: {len(_server._resources)} | "
            f"Prompts: {len(_server._prompts)}",
            file=sys.stderr,
        )

    # ── Helpers ─────────────────────────────────────────────

    def _validate_origin(request: Request) -> bool:
        """Validate Origin header to prevent DNS rebinding."""
        origin = request.headers.get("origin")
        if origin is None:
            return True
        try:
            parsed = urlparse(origin)
            return parsed.hostname in ("localhost", "127.0.0.1", "0.0.0.0")
        except Exception:
            return False

    def _json_error(status: int, code: int, message: str) -> JSONResponse:
        return JSONResponse(
            status_code=status,
            content=json.loads(rpc_error(None, code, message)),
        )

    def _add_protocol_header(resp: Response) -> Response:
        resp.headers["Mcp-Protocol-Version"] = PROTOCOL_VERSION
        return resp

    async def _dispatch(message: Any) -> Optional[str]:
        """Run synchronous dispatch() in a thread pool to avoid blocking."""
        return await asyncio.to_thread(_server.dispatch, message)

    # ── POST /mcp — JSON-RPC requests ──────────────────────

    # ── Bearer-token authentication (Vault-backed) ───────

    _cached_token: Optional[str] = None
    _token_expires_at: float = 0.0

    def _get_active_token() -> Optional[str]:
        """Ожидаемый Bearer-токен: Vault (с кешем TTL) -> env fallback.

        Логика:
        - Если задан FREEBUFF_VAULT_ADDR: идём в Vault через hvac.
          Поддерживает AppRole (FREEBUFF_VAULT_ROLE_ID + _SECRET_ID)
          или root-token (FREEBUFF_VAULT_TOKEN).
          Результат кешируется на FREEBUFF_VAULT_TOKEN_CACHE_TTL (default 300).
          Если Vault недоступен — возвращаем None (fail-closed).
        - Если FREEBUFF_VAULT_ADDR не задан: возвращаем FREEBUFF_MCP_TOKEN
          напрямую (env-only path). Кеш для этого path НЕ используется —
          это позволяет тестам подменять токен через monkeypatch.
        """
        global _cached_token, _token_expires_at
        now = time.time()
        if _cached_token is not None and now < _token_expires_at:
            return _cached_token

        vault_addr = os.getenv("FREEBUFF_VAULT_ADDR")
        if not vault_addr:
            # env-only path, no cache (для тестов и dev)
            return os.getenv("FREEBUFF_MCP_TOKEN")

        if not HAS_HVAC:
            print(
                "[mcp_fastapi] hvac не установлен — /mcp будет закрыт",
                file=sys.stderr,
            )
            return None

        try:
            client = hvac.Client(url=vault_addr)
            role_id = os.getenv("FREEBUFF_VAULT_ROLE_ID")
            secret_id = os.getenv("FREEBUFF_VAULT_SECRET_ID")
            vault_token = os.getenv("FREEBUFF_VAULT_TOKEN")

            if role_id and secret_id:
                client.auth.approle.login(
                    role_id=role_id, secret_id=secret_id
                )
            elif vault_token:
                client.token = vault_token
            else:
                print(
                    "[mcp_fastapi] FREEBUFF_VAULT_ADDR задан, но без auth — "
                    "fail-closed",
                    file=sys.stderr,
                )
                return None

            path = os.getenv(
                "FREEBUFF_VAULT_PATH", "freebuff/mcp"
            )
            # hvac python принимает путь без префикса mount/data/.
            # Поддерживаем несколько стандартных mount-ов (secret, kv, kv2 и пр.)
            if "/data/" in path:
                idx = path.find("/data/") + len("/data/")
                path = path[idx:]
            key = os.getenv("FREEBUFF_VAULT_KEY", "token")

            resp = client.secrets.kv.v2.read_secret_version(path=path)
            token = resp["data"]["data"].get(key)
            if not isinstance(token, str) or not token:
                return None

            ttl_sec = float(
                os.getenv("FREEBUFF_VAULT_TOKEN_CACHE_TTL", "300")
            )
            _cached_token = token
            _token_expires_at = now + ttl_sec
            return token
        except Exception as e:
            print(
                f"[mcp_fastapi] Vault fetch failed: {e}",
                file=sys.stderr,
            )
            return None

    def _reset_token_cache() -> None:
        """Принудительный сброс кеша (для тестов с monkeypatch)."""
        global _cached_token, _token_expires_at
        _cached_token = None
        _token_expires_at = 0.0

    def _unauthorized() -> HTTPException:
        """401 + WWW-Authenticate header (RFC 6750)."""
        return HTTPException(
            status_code=401,
            detail={
                "error": {
                    "code": INVALID_REQUEST,
                    "message": "Unauthorized",
                }
            },
            headers={"WWW-Authenticate": 'Bearer realm="buffy-mcp"'},
        )

    def verify_bearer_token(request: Request) -> None:
        """FastAPI Depends: проверяет Authorization: Bearer <token>.

        Bypass возможен ТОЛЬКО при FREEBUFF_ENV=test И FREEBUFF_MCP_AUTH_DISABLED=1
        (двойной lock — случайное включение bypass в production невозможно).
        Сравнение токенов — через hmac.compare_digest (constant-time).
        """
        if (
            os.getenv("FREEBUFF_ENV") == "test"
            and os.getenv("FREEBUFF_MCP_AUTH_DISABLED") == "1"
        ):
            return

        auth = request.headers.get("authorization", "")
        if not auth.startswith("Bearer "):
            raise _unauthorized()
        provided = auth[len("Bearer ") :].strip()
        # DoS-защита: токены реалистично ≤1KB; больше — сразу 401
        if len(provided) > 1024:
            raise _unauthorized()
        expected = _get_active_token()
        if not expected:
            raise _unauthorized()
        if not hmac.compare_digest(
            provided.encode("utf-8"),
            expected.encode("utf-8"),
        ):
            raise _unauthorized()

    @app.post("/mcp")
    async def mcp_post(
        request: Request,
        _auth: None = Depends(verify_bearer_token),
    ) -> Response:
        if not _validate_origin(request):
            return _json_error(403, INVALID_REQUEST, "Invalid Origin header")

        try:
            body = await request.json()
        except Exception:
            return _json_error(400, PARSE_ERROR, "Invalid JSON")

        # initialize → create new session
        if isinstance(body, dict) and body.get("method") == "initialize":
            session_id = await _sessions.create_session()
            response = await _dispatch(body)
            if response:
                resp: Response = JSONResponse(content=json.loads(response))
            else:
                resp = Response(status_code=202)
            resp.headers["Mcp-Session-Id"] = session_id
            return _add_protocol_header(resp)

        # Validate session for non-initialize POSTs
        session_id = request.headers.get("Mcp-Session-Id")
        if session_id:
            session = await _sessions.get_session(session_id)
            if not session:
                return _json_error(404, INVALID_REQUEST, "Session not found")

        # Batch request
        if isinstance(body, list):
            responses = []
            for msg in body:
                r = await _dispatch(msg)
                if r:
                    responses.append(json.loads(r))
            if responses:
                return _add_protocol_header(JSONResponse(content=responses))
            return _add_protocol_header(Response(status_code=202))

        # Single request
        is_notification = isinstance(body, dict) and body.get("id") is None
        response = await _dispatch(body)

        if is_notification or response is None:
            return _add_protocol_header(Response(status_code=202))
        return _add_protocol_header(JSONResponse(content=json.loads(response)))

    # ── GET /mcp — SSE notification stream ──────────────────

    @app.get("/mcp")
    async def mcp_get(
        request: Request,
        _auth: None = Depends(verify_bearer_token),
    ) -> Response:
        if not _validate_origin(request):
            return _json_error(403, INVALID_REQUEST, "Invalid Origin header")

        session_id = request.headers.get("Mcp-Session-Id")
        if not session_id:
            return _json_error(
                400, INVALID_REQUEST, "Mcp-Session-Id required for GET"
            )

        session = await _sessions.get_session(session_id)
        if not session:
            return _json_error(404, INVALID_REQUEST, "Session not found")

        async def event_stream():
            while session.active:
                try:
                    msg = await asyncio.wait_for(
                        session.notification_queue.get(), timeout=30
                    )
                    yield f"data: {msg}\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Mcp-Protocol-Version": PROTOCOL_VERSION,
            },
        )

    # ── DELETE /mcp — session termination ───────────────────

    @app.delete("/mcp")
    async def mcp_delete(
        request: Request,
        _auth: None = Depends(verify_bearer_token),
    ) -> Response:
        if not _validate_origin(request):
            return _json_error(403, INVALID_REQUEST, "Invalid Origin header")

        session_id = request.headers.get("Mcp-Session-Id")
        if not session_id:
            return _json_error(400, INVALID_REQUEST, "Mcp-Session-Id required")

        if await _sessions.delete_session(session_id):
            resp = Response(status_code=204)
            return _add_protocol_header(resp)
        return _json_error(404, INVALID_REQUEST, "Session not found")

    # ── GET / — health check ────────────────────────────────

    @app.get("/")
    async def health() -> dict:
        return {
            "status": "ok",
            "server": "buffy-mcp",
            "protocol": PROTOCOL_VERSION,
            "endpoint": "/mcp",
            "transport": "streamable-http",
            "dashboard": "/dashboard",
        }

    # ── GET /dashboard — Metrics Dashboard (HTML) ────────────

    @app.get("/dashboard")
    async def metrics_dashboard():
        """Serve the Metrics Dashboard HTML page."""
        dashboard_path = WORKSPACE / "buffy-playground" / "public" / "metrics-dashboard.html"
        if not dashboard_path.exists():
            return JSONResponse(
                status_code=404,
                content={"error": "Dashboard not found"},
            )
        from fastapi.responses import HTMLResponse
        html = dashboard_path.read_text(encoding="utf-8")
        return HTMLResponse(content=html)

    # ── Metrics helper ──────────────────────────────────────

    def _get_metrics() -> Any:
        """Lazy init of MetricsEngine."""
        global _metrics
        if _metrics is None:
            from scripts_01.metrics import MetricsEngine
            _metrics = MetricsEngine()
        return _metrics

    def _metrics_response(data: dict, fmt: str) -> JSONResponse | dict:
        """Return JSONResponse or plain dict based on format."""
        if fmt == "json":
            return JSONResponse(content=data)
        # text format: pretty-print interpretation
        lines = []
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{key}:")
                for k, v in value.items():
                    lines.append(f"  {k}: {v}")
            else:
                lines.append(f"{key}: {value}")
        return {"content": "\n".join(lines), "format": "text"}

    def _metric_to_dict(m: Any) -> dict:
        from dataclasses import asdict
        return asdict(m)

    # ── GET /metrics/report — полный отчёт ──────────────────

    @app.get("/metrics/report")
    async def metrics_report(fmt: str = "json"):
        """Full metrics report with all 5 metrics."""
        engine = _get_metrics()
        try:
            report = engine.compute_report(save=False)
            data = report.to_dict()
            data["health_score"] = _compute_health_score_fn(report)
            return _metrics_response(data, fmt)
        except Exception as e:
            return _metrics_response({"error": str(e)}, fmt)

    # ── GET /metrics/{name} — одна метрика ──────────────────

    def _compute_health_score_fn(report: Any) -> int:
        from scripts_01.metrics import _compute_health_score
        return _compute_health_score(report)

    @app.get("/metrics/vcr")
    async def metrics_vcr(fmt: str = "json"):
        engine = _get_metrics()
        return _metrics_response(_metric_to_dict(engine.compute_vcr()), fmt)

    @app.get("/metrics/srg")
    async def metrics_srg(fmt: str = "json"):
        engine = _get_metrics()
        return _metrics_response(_metric_to_dict(engine.compute_srg()), fmt)

    @app.get("/metrics/cpvo")
    async def metrics_cpvo(fmt: str = "json"):
        engine = _get_metrics()
        return _metrics_response(_metric_to_dict(engine.compute_cpvo()), fmt)

    @app.get("/metrics/rrr")
    async def metrics_rrr(fmt: str = "json"):
        engine = _get_metrics()
        return _metrics_response(_metric_to_dict(engine.compute_rrr()), fmt)

    @app.get("/metrics/ttd")
    async def metrics_ttd(fmt: str = "json"):
        engine = _get_metrics()
        return _metrics_response(_metric_to_dict(engine.compute_ttd()), fmt)

    # ── GET /metrics/trend/{name} — тренд метрики ───────────

    @app.get("/metrics/trend/{name)")
    async def metrics_trend(name: str, limit: int = 10, fmt: str = "json"):
        engine = _get_metrics()
        available = {"vcr", "srg", "cpvo", "rrr", "ttd"}
        if name not in available:
            return _metrics_response(
                {"error": f"Unknown metric: {name}. Available: {', '.join(sorted(available))}"},
                fmt,
            )
        history = engine.get_trend(name, limit=limit)
        return _metrics_response({"metric": name, "history": history}, fmt)

    # ── GET /metrics/status — статус Metrics Engine ─────────

    @app.get("/metrics/status")
    async def metrics_status(fmt: str = "json"):
        engine = _get_metrics()
        return _metrics_response(engine.get_status(), fmt)

    # ── GET /sync/status — Remote Sync status for Flutter UI indicator (Phase 5.4) ──
    #
    # Polled by projects_17/freebuff_flutter_app/lib/sync_status.dart every
    # poll_interval_sec (manifest remote_sync.indicator.poll_interval_sec).
    # Same snapshot shape as MCP tool `sync_status` in freebuff_plugin_03.
    # Open (no Bearer) like /metrics/* and / — local-device status read,
    # exposes no secrets, only closed-vocab status + counts.

    @app.get("/sync/status")
    async def sync_status() -> JSONResponse:
        """Live remote-sync status snapshot (idle/connected/conflict/quarantine).

        Response: {"success": true, "data": {status, listener_running,
          pending_count, conflict_count, quarantine_count, last_event,
          registered, timestamp_ms]]

        If no coordinator is registered, returns idle with registered=false
        (soft-fallback per CAN-14 — never raises).
        """
        try:
            from core_02.remote_sync import (
                derive_sync_status,
                get_active_coordinator,
            )

            coord = get_active_coordinator()
            if coord is None:
                snapshot = {"status": "idle", "registered": False}
            else:
                snapshot = derive_sync_status(coord)
                snapshot["registered"] = True
            return JSONResponse(content={"success": True, "data": snapshot})
        except Exception as e:
            return _policy_error(500, f"sync status failed: {e}")

    # ── POST /policy/override — User-Choice Override без MCP ──

    def _get_policy_engine() -> Optional[Any]:
        """Lazy init PolicyEngine (правило 11, User-Choice Override)."""
        global _policy_engine
        if _policy_engine is None:
            try:
                from freebuff_plugin_03.policy import PolicyEngine
                if _server is None:
                    return None
                registry = _server._get_runtime_registry()
                cap_reg = getattr(_server, "_runtime_capability_registry", None)
                if registry is None or cap_reg is None:
                    return None
                _policy_engine = PolicyEngine(registry, cap_reg)
            except Exception as e:
                print(
                    f"[mcp_fastapi] PolicyEngine init failed: {e}",
                    file=sys.stderr,
                )
                return None
        return _policy_engine

    def _policy_error(status: int, message: str) -> JSONResponse:
        """Единый контракт ошибок для REST-эндпоинтов policy/*.

        Намеренно отличается от _json_error (JSON-RPC shape
        {error: {code, message}}): REST-клиенты получают {success, error} —
        тот же контракт, что у инструмента policy_override в MCP-сервере
        ({success, data} / {success: False, error}).
        """
        return JSONResponse(
            status_code=status,
            content={"success": False, "error": message},
        )

    @app.post("/policy/override")
    async def policy_override(
        request: Request,
        _auth: None = Depends(verify_bearer_token),
    ) -> Response:
        """Применить диалоговое переопределение (правило 11) без MCP.

        Тело: {"message": "use deepseek instead of claude for coding",
               "capability": "research" (опц., переопределяет capability из фразы),
               "dry_run": true (опц., показать распознанный интент БЕЗ записи)]
        Ответ: {"success": true, "data": {applied, dry_run, capability, runtime,
                previous_runtime, matched, message]]
        """
        if not _validate_origin(request):
            return _policy_error(403, "Invalid Origin header")

        try:
            body = await request.json()
        except Exception:
            return _policy_error(400, "Invalid JSON")

        message = body.get("message") if isinstance(body, dict) else None
        if not message or not isinstance(message, str):
            return _policy_error(400, "message (string) is required")

        capability = body.get("capability") if isinstance(body, dict) else None
        if capability is not None and (
            not isinstance(capability, str) or not capability.strip()
        ):
            return _policy_error(400, "capability (non-empty string) expected")

        dry_run = body.get("dry_run", False) if isinstance(body, dict) else False
        if not isinstance(dry_run, bool):
            return _policy_error(400, "dry_run (boolean) expected")

        # Sync-работа (ленивая инициализация PolicyEngine + парсинг/применение
        # фразы) выполняется в thread pool — как _dispatch для /mcp — чтобы не
        # блокировать event loop (init кешируется, блокировка разовая).
        engine = await asyncio.to_thread(_get_policy_engine)
        if engine is None and not dry_run:
            return _policy_error(
                503, "PolicyEngine not available — override not applied"
            )

        try:
            from freebuff_plugin_03.policy import apply_override
            result = await asyncio.to_thread(
                apply_override, message, engine, capability, dry_run
            )
        except Exception as e:
            return _policy_error(500, f"Policy override failed: {e}")

        if result is None:
            return _policy_error(
                422,
                "Could not parse override intent from message. "
                'Examples: "use deepseek instead of claude for coding", '
                '"используй freebuff для research"',
            )

        # Опубликовать событие ТОЛЬКО при реальном применении (не dry_run),
        # и если сервер запущен (_publish None-safe)
        if not dry_run and _server is not None:
            try:
                _server._publish("policy.override", {
                    "capability": result.get("capability"),
                    "runtime": result.get("runtime"),
                    "matched": result.get("matched"),
                })
            except Exception:
                pass

        return JSONResponse(content={"success": True, "data": result})

    # ── GET /policy/status — текущие предпочтения (правило 11) ──

    @app.get("/policy/status")
    async def policy_status(
        request: Request,
        _auth: None = Depends(verify_bearer_token),
    ) -> Response:
        """Текущие предпочтения из policies.json (правило 11) без MCP.

        Ответ: {"success": true, "data": {"count": N, "preferences": {...},
                "policies": {capability: {preferred_runtime, fallback_chain,
                constraints]]]]
        """
        if not _validate_origin(request):
            return _policy_error(403, "Invalid Origin header")

        engine = await asyncio.to_thread(_get_policy_engine)
        if engine is None:
            return _policy_error(
                503, "PolicyEngine not available — status unavailable"
            )

        # list_policies() — тривиальная копия dict(self._policies), падать нечему
        policies = await asyncio.to_thread(engine.list_policies)

        # DRY: сериализация через канонический дамп PolicyEngine
        # (тот же формат, что в save_policy -> policies.json)
        from freebuff_plugin_03.policy import PolicyEngine
        preferences: Dict[str, str] = {}
        serialized: Dict[str, dict] = {}
        for cap, policy in policies.items():
            if policy is None:
                continue
            preferred = getattr(policy, "preferred_runtime", None)
            if preferred:
                preferences[cap] = preferred
            serialized[cap] = PolicyEngine._dump_capability_policy(policy)

        return JSONResponse(content={
            "success": True,
            "data": {
                "count": len(serialized),
                "preferences": preferences,
                "policies": serialized,
            },
        })

    # ── /api/v1/* — Meeting Tasks REST (для 043 frontend dashboard) ──
    #
    # Канон: pompts_11/042_06_dokumentaciya_meeting_tasks.md, Фаза E + 043 §5
    # (api.ts: getProjects/getTasks/createTask). Запросы по /api/v1/* идут
    # через тот же bearer-auth, что и /mcp и /policy/* (REST-bypass политика
    # применяется). Soft-fallback на отсутствующую таблицу projects:
    # возвращаем пустой список с success=true, чтобы frontend мог
    # монтироваться до scan_projects.

    @app.get("/api/v1/projects")
    async def list_projects(
        _auth: None = Depends(verify_bearer_token),
    ) -> JSONResponse:
        """Список проектов из таблицы projects (для 043 frontend)."""
        try:
            db_path = task_manager.DB_PATH
            conn = task_manager.init_db(db_path)
            try:
                has = conn.execute(
                    "SELECT 1 FROM sqlite_master "
                    "WHERE type='table' AND name='projects'"
                ).fetchone() is not None
                projects: list[dict[str, str]] = []
                if has:
                    rows = conn.execute(
                        "SELECT name, description, status, last_scanned "
                        "FROM projects ORDER BY name"
                    ).fetchall()
                    projects = [
                        {
                            "name": r[0],
                            "description": r[1] or "",
                            "status": r[2] or "active",
                            "last_scanned": r[3],
                        }
                        for r in rows
                    ]
            finally:
                conn.close()
            return JSONResponse(content={
                "success": True,
                "data": {"projects": projects, "count": len(projects)},
            })
        except Exception as e:
            return _policy_error(500, f"projects list failed: {e}")

    @app.get("/api/v1/tasks")
    async def list_tasks_api(
        project_id: str,
        type: str | None = None,
        status: str | None = None,
        _auth: None = Depends(verify_bearer_token),
    ) -> JSONResponse:
        """Задачи проекта через task_manager.get_tasks (опц. фильтры)."""
        try:
            tasks = task_manager.get_tasks(
                project_id, task_type=type, status=status,
                db_path=task_manager.DB_PATH,
            )
            return JSONResponse(content={
                "success": True,
                "data": {"tasks": tasks, "count": len(tasks)},
            })
        except ValueError as e:
            return _policy_error(400, str(e))
        except Exception as e:
            return _policy_error(500, f"tasks list failed: {e}")

    @app.post("/api/v1/tasks")
    async def create_task_api(
        request: Request,
        _auth: None = Depends(verify_bearer_token),
    ) -> JSONResponse:
        """Создать задачу через task_manager.create_task.

        Body: {"project_id": "...", "title": "...", "task_type": "...",
               "description": "...", "priority": "...", "meeting_time": "...",
               "location": "...", "participants": ["..."]]
        """
        try:
            body = await request.json()
        except Exception:
            return _policy_error(400, "Invalid JSON")
        if not isinstance(body, dict):
            return _policy_error(400, "Body must be JSON object")
        project_id = body.get("project_id")
        title = body.get("title")
        if not project_id or not isinstance(project_id, str):
            return _policy_error(400, "project_id (non-empty string) required")
        if not title or not isinstance(title, str):
            return _policy_error(400, "title (non-empty string) required")
        try:
            task = task_manager.create_task(
                project_id,
                title,
                task_type=str(body.get("task_type", "digital")),
                description=str(body.get("description", "")),
                priority=str(body.get("priority", "normal")),
                meeting_time=body.get("meeting_time"),
                location=body.get("location"),
                participants=body.get("participants"),
                db_path=task_manager.DB_PATH,
            )
            return JSONResponse(
                status_code=201,
                content={"success": True, "data": {"task": task}},
            )
        except ValueError as e:
            return _policy_error(400, str(e))
        except Exception as e:
            return _policy_error(500, f"task create failed: {e}")


# ═══════════════════════════════════════════════════════════════
# Cloudflare Tunnel helpers
# ═══════════════════════════════════════════════════════════════


def _print_tunnel_config(url: str) -> None:
    """Print Claude/Gemini MCP config for the tunnel URL."""
    config = {
        "mcpServers": {
            "buffy": {
                "url": f"{url}/mcp",
                "transport": "streamable-http",
            }
        }
    }
    print(f"\n{'=' * 60}", file=sys.stderr)
    print(f"🔗 Public MCP endpoint: {url}/mcp", file=sys.stderr)
    print(f"\n📋 Claude Desktop / Gemini config:", file=sys.stderr)
    print(json.dumps(config, indent=2), file=sys.stderr)
    print(f"{'=' * 60}\n", file=sys.stderr)


def _start_tunnel(port: int) -> Optional[subprocess.Popen]:
    """Start cloudflared tunnel subprocess. Returns Popen or None."""
    try:
        proc = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", f"http://localhost:{port}"],
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            text=True,
        )
    except FileNotFoundError:
        print(
            "❌ cloudflared not installed.\n"
            "   Install: pkg install cloudflared",
            file=sys.stderr,
        )
        return None
    except Exception as e:
        print(f"❌ cloudflared error: {e}", file=sys.stderr)
        return None

    url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

    def _read_stderr() -> None:
        for line in proc.stderr:
            line_s = line.strip()
            if line_s:
                print(f"  [cloudflared] {line_s}", file=sys.stderr)
            match = url_pattern.search(line_s)
            if match:
                _print_tunnel_config(match.group(0))

    reader = threading.Thread(target=_read_stderr, daemon=True)
    reader.start()
    return proc


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Buffy MCP Server — FastAPI + Cloudflare Tunnel",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python scripts_01/mcp_fastapi.py                         # localhost:8765
  python scripts_01/mcp_fastapi.py --port 8000             # custom port
  python scripts_01/mcp_fastapi.py --tunnel                # + Cloudflare Tunnel
  python scripts_01/mcp_fastapi.py --tunnel --port 8000    # custom port + tunnel

Cloudflare Tunnel gives a public HTTPS URL:
  https://xxx-xxx-xxx.trycloudflare.com/mcp

Claude Desktop config:
  {
    "mcpServers": {
      "buffy": {
        "url": "https://YOUR-TUNNEL.trycloudflare.com/mcp",
        "transport": "streamable-http"
      }
    }
  }
""",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind host (default: 127.0.0.1, use 0.0.0.0 for all interfaces)",
    )
    parser.add_argument("--port", type=int, default=8765, help="Bind port (default: 8765)")
    parser.add_argument(
        "--tunnel",
        action="store_true",
        help="Start Cloudflare Tunnel for public HTTPS access",
    )

    args = parser.parse_args()

    if not HAS_FASTAPI:
        print(
            "❌ FastAPI not installed. Run: pip install fastapi uvicorn",
            file=sys.stderr,
        )
        sys.exit(1)

    # Start Cloudflare Tunnel
    tunnel_proc: Optional[subprocess.Popen] = None
    if args.tunnel:
        print("🌐 Starting Cloudflare Tunnel...", file=sys.stderr)
        tunnel_proc = _start_tunnel(args.port)

    # Start uvicorn
    import uvicorn

    print(f"\n🚀 Buffy MCP FastAPI Server", file=sys.stderr)
    print(f"   Endpoint: http://{args.host}:{args.port}/mcp", file=sys.stderr)
    print(f"   Protocol: {PROTOCOL_VERSION}", file=sys.stderr)
    if args.tunnel:
        print(f"   Tunnel:   starting...", file=sys.stderr)
    print(f"   Press Ctrl+C to stop\n", file=sys.stderr)

    try:
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            log_level="info",
        )
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...", file=sys.stderr)
    finally:
        if tunnel_proc:
            tunnel_proc.terminate()
            tunnel_proc.wait(timeout=5)
            print("🌐 Cloudflare Tunnel stopped", file=sys.stderr)


if __name__ == "__main__":
    main()
