#!/usr/bin/env python3
"""
mcp_fastapi.py — FastAPI wrapper for Buffy MCP Server.

Exposes MCP Streamable HTTP protocol via FastAPI + uvicorn.
Supports Cloudflare Tunnel for public HTTPS access.

Protocol: MCP 2025-03-26 Streamable HTTP
  - POST /mcp: JSON-RPC requests → application/json or 202 Accepted
  - GET  /mcp: SSE notification stream (text/event-stream)
  - DELETE /mcp: session termination (204 No Content)

Usage:
    python scripts/mcp_fastapi.py                         # localhost:8765
    python scripts/mcp_fastapi.py --port 8000             # custom port
    python scripts/mcp_fastapi.py --tunnel                # + Cloudflare Tunnel
    python scripts/mcp_fastapi.py --tunnel --port 8000    # custom port + tunnel

    uvicorn scripts.mcp_fastapi:app --host 0.0.0.0 --port 8765

Claude Desktop config (Streamable HTTP):
    {
      "mcpServers": {
        "buffy": {
          "url": "https://YOUR-TUNNEL.trycloudflare.com/mcp",
          "transport": "streamable-http"
        ***REMOVED***
      ***REMOVED***
    ***REMOVED***
"""

from __future__ import annotations

import asyncio
import json
***REMOVED***
import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
***REMOVED***
from typing import Any, Dict, Optional
from urllib.parse import urlparse

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

from scripts.mcp_server import (
    BuffyMcpServer,
    PROTOCOL_VERSION,
    PARSE_ERROR,
    INVALID_REQUEST,
    rpc_error,
)

try:
    from fastapi import FastAPI, Request, Response
    from fastapi.responses import JSONResponse, StreamingResponse

    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


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
        self._sessions: Dict[str, McpAsyncSession***REMOVED*** = {***REMOVED***
        self._lock = asyncio.Lock()

    async def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        async with self._lock:
            self._sessions[session_id***REMOVED*** = McpAsyncSession(session_id=session_id)
        return session_id

    async def get_session(self, session_id: str) -> Optional[McpAsyncSession***REMOVED***:
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

    _server: Optional[BuffyMcpServer***REMOVED*** = None
    _sessions: Optional[McpAsyncSessionManager***REMOVED*** = None

    @app.on_event("startup")
    async def _startup() -> None:
        global _server, _sessions
        _server = BuffyMcpServer()
        _sessions = McpAsyncSessionManager()
        print(
            f"🚀 Buffy MCP FastAPI server started\n"
            f"   Protocol: {PROTOCOL_VERSION***REMOVED***\n"
            f"   Tools: {len(_server._tools)***REMOVED*** | "
            f"Resources: {len(_server._resources)***REMOVED*** | "
            f"Prompts: {len(_server._prompts)***REMOVED***",
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
        resp.headers["Mcp-Protocol-Version"***REMOVED*** = PROTOCOL_VERSION
        return resp

    async def _dispatch(message: Any) -> Optional[str***REMOVED***:
        """Run synchronous dispatch() in a thread pool to avoid blocking."""
        return await asyncio.to_thread(_server.dispatch, message)

    # ── POST /mcp — JSON-RPC requests ──────────────────────

    @app.post("/mcp")
    async def mcp_post(request: Request) -> Response:
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
            resp.headers["Mcp-Session-Id"***REMOVED*** = session_id
            return _add_protocol_header(resp)

        # Validate session for non-initialize POSTs
        session_id = request.headers.get("Mcp-Session-Id")
        if session_id:
            session = await _sessions.get_session(session_id)
            if not session:
                return _json_error(404, INVALID_REQUEST, "Session not found")

        # Batch request
        if isinstance(body, list):
            responses = [***REMOVED***
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
    async def mcp_get(request: Request) -> Response:
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
                    yield f"data: {msg***REMOVED***\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Mcp-Protocol-Version": PROTOCOL_VERSION,
            ***REMOVED***,
        )

    # ── DELETE /mcp — session termination ───────────────────

    @app.delete("/mcp")
    async def mcp_delete(request: Request) -> Response:
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
        ***REMOVED***


# ═══════════════════════════════════════════════════════════════
# Cloudflare Tunnel helpers
# ═══════════════════════════════════════════════════════════════


def _print_tunnel_config(url: str) -> None:
    """Print Claude/Gemini MCP config for the tunnel URL."""
    config = {
        "mcpServers": {
            "buffy": {
                "url": f"{url***REMOVED***/mcp",
                "transport": "streamable-http",
            ***REMOVED***
        ***REMOVED***
    ***REMOVED***
    print(f"\n{'=' * 60***REMOVED***", file=sys.stderr)
    print(f"🔗 Public MCP endpoint: {url***REMOVED***/mcp", file=sys.stderr)
    print(f"\n📋 Claude Desktop / Gemini config:", file=sys.stderr)
    print(json.dumps(config, indent=2), file=sys.stderr)
    print(f"{'=' * 60***REMOVED***\n", file=sys.stderr)


def _start_tunnel(port: int) -> Optional[subprocess.Popen***REMOVED***:
    """Start cloudflared tunnel subprocess. Returns Popen or None."""
    try:
        proc = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", f"http://localhost:{port***REMOVED***"***REMOVED***,
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
        print(f"❌ cloudflared error: {e***REMOVED***", file=sys.stderr)
        return None

    url_pattern = re.compile(r"https://[a-zA-Z0-9-***REMOVED***+\.trycloudflare\.com")

    def _read_stderr() -> None:
        for line in proc.stderr:
            line_s = line.strip()
            if line_s:
                print(f"  [cloudflared***REMOVED*** {line_s***REMOVED***", file=sys.stderr)
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
  python scripts/mcp_fastapi.py                         # localhost:8765
  python scripts/mcp_fastapi.py --port 8000             # custom port
  python scripts/mcp_fastapi.py --tunnel                # + Cloudflare Tunnel
  python scripts/mcp_fastapi.py --tunnel --port 8000    # custom port + tunnel

Cloudflare Tunnel gives a public HTTPS URL:
  https://xxx-xxx-xxx.trycloudflare.com/mcp

Claude Desktop config:
  {
    "mcpServers": {
      "buffy": {
        "url": "https://YOUR-TUNNEL.trycloudflare.com/mcp",
        "transport": "streamable-http"
      ***REMOVED***
    ***REMOVED***
  ***REMOVED***
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
    tunnel_proc: Optional[subprocess.Popen***REMOVED*** = None
    if args.tunnel:
        print("🌐 Starting Cloudflare Tunnel...", file=sys.stderr)
        tunnel_proc = _start_tunnel(args.port)

    # Start uvicorn
    import uvicorn

    print(f"\n🚀 Buffy MCP FastAPI Server", file=sys.stderr)
    print(f"   Endpoint: http://{args.host***REMOVED***:{args.port***REMOVED***/mcp", file=sys.stderr)
    print(f"   Protocol: {PROTOCOL_VERSION***REMOVED***", file=sys.stderr)
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
