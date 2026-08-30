#!/usr/bin/env python3
"""scripts_01/continue_endpoint.py — HTTP /api/continue endpoint для auto_continue.sh.

Лёгкий HTTP-сервер (без FastAPI/Flask — только stdlib).
Принимает POST /api/continue, обновляет маркер-файл, логирует запросы.

Usage:
    python3 scripts_01/continue_endpoint.py [--port PORT] [--marker PATH]

    Фоновый запуск:
    nohup python3 scripts_01/continue_endpoint.py --port 8081 &

Endpoints:
    POST /api/continue  — подтвердить продолжение сессии
    GET  /api/status    — статус (последний continue, uptime)
    GET  /api/ping      — healthcheck (всегда 200)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
}
from datetime import datetime, timezone


# ─── Состояние ────────────────────────────────────────────────────────────

class SessionState:
    def __init__(self, marker_path: str):
        self.marker_path = Path(marker_path)
        self.started_at = time.time()
        self.last_continue_at: float | None = None
        self.continue_count = 0

    def touch(self) -> None:
        """Обновить маркер-файл и состояние."""
        self.last_continue_at = time.time()
        self.continue_count += 1
        self.marker_path.parent.mkdir(parents=True, exist_ok=True)
        self.marker_path.write_text(
            json.dumps({
                "last_continue": datetime.now(timezone.utc).isoformat(),
                "continue_count": self.continue_count,
                "started_at": datetime.fromtimestamp(
                    self.started_at, tz=timezone.utc
                ).isoformat(),
            ], indent=2)
        )

    def status(self) -> dict:
        uptime = time.time() - self.started_at
        last = self.last_continue_at
        return {
            "status": "ok",
            "uptime_seconds": round(uptime, 1),
            "continue_count": self.continue_count,
            "last_continue_at": (
                datetime.fromtimestamp(last, tz=timezone.utc).isoformat()
                if last else None
            ),
            "last_continue_ago_seconds": (
                round(time.time() - last, 1) if last else None
            ),
        }


# ─── HTTP Handler ─────────────────────────────────────────────────────────

class ContinueHandler(BaseHTTPRequestHandler):
    state: SessionState | None = None  # инжектится перед стартом

    def log_message(self, fmt, *args):
        """Логируем только ошибки (4xx/5xx)."""
        if "40" in fmt or "50" in fmt:
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"[{ts}] {fmt % args}", file=sys.stderr)

    def _json(self, code: int, data: dict) -> None:
        body = json.dumps(data, ensure_ascii=False, indent=2)
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body.encode())

    def do_OPTIONS(self):
        """CORS preflight."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/ping":
            self._json(200, {"ping": "pong", "timestamp": datetime.now(timezone.utc).isoformat()})
        elif self.path == "/api/status":
            s = self.state or SessionState("")
            self._json(200, s.status())
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/api/continue":
            if not self.state:
                self._json(500, {"error": "server not initialized"})
                return
            self.state.touch()
            self._json(200, {
                "message": "continue acknowledged",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **self.state.status(),
            ])
        else:
            self._json(404, {"error": "not found"})


# ─── CLI ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Continue endpoint for Freebuff auto-continue")
    parser.add_argument("--port", type=int, default=8081, help="Порт (default: 8081)")
    parser.add_argument(
        "--marker", type=str,
        default=os.path.expanduser("~/.freebuff_continue_marker.json"),
        help="Путь к маркер-файлу",
    )
    args = parser.parse_args()

    state = SessionState(args.marker)
    ContinueHandler.state = state

    server = HTTPServer(("0.0.0.0", args.port), ContinueHandler)
    print(f"✅ Continue endpoint: http://0.0.0.0:{args.port}")
    print(f"   POST /api/continue — подтвердить сессию")
    print(f"   GET  /api/status   — статус")
    print(f"   GET  /api/ping     — healthcheck")
    print(f"   Маркер: {args.marker}")
    print(f"   PID: {os.getpid()}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Остановлен.")
        server.server_close()


if __name__ == "__main__":
    main()
