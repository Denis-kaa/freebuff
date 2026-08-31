#!/usr/bin/env python3
"""
dashboard_api.py — FastAPI сервер для Buffy Dashboard.

Запуск:
    python scripts_01/dashboard_api.py
    # или: uvicorn scripts.dashboard_api:app --host 0.0.0.0 --port 8080

Эндпоинты:
    GET /api/system          — информация о системе
    GET /api/tests           — результаты тестов (pytest)
    GET /api/sessions        — список сессий
    GET /api/sessions_15/{id}   — детали сессии
    GET /api/sessions_15/{id}/messages — сообщения сессии
    GET /api/memory          — статистика памяти
    GET /api/events          — последние события
    GET /api/events/stats    — статистика событий
    GET /api/knowledge       — статистика базы знаний
    GET /api/git             — git статус
    GET /api/checkpoints     — последние чекпоинты
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Путь к корню freebuff
WORKSPACE = Path(__file__).resolve().parent.parent
os.chdir(str(WORKSPACE))

app = FastAPI(
    title="Buffy Dashboard API",
    version="1.0.0",
    description="API для дашборда состояния системы Buffy",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:4173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Хелперы ───────────────────────────────────────────────────

def _safe_run(cmd: list[str], timeout: int = 10) -> str:
    """Безопасный запуск команды, возвращает stdout или ошибку."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() or r.stderr.strip()
    except Exception as e:
        return f"error: {e}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ═══════════════════════════════════════════════════════════════
# Эндпоинты
# ═══════════════════════════════════════════════════════════════

@app.get("/api/system")
async def get_system_info() -> dict[str, Any]:
    """Информация о системе: ОС, Python, Node, RAM, аптайм."""
    try:
        import psutil
        ram = psutil.virtual_memory()
        ram_info = {
            "total_gb": round(ram.total / (1024**3), 1),
            "available_gb": round(ram.available / (1024**3), 1),
            "percent_used": ram.percent,
            "usage_percent": ram.percent,
        }
        cpu_percent = psutil.cpu_percent(interval=0.5)
        disk = psutil.disk_usage(str(WORKSPACE))
        disk_info = {
            "total_gb": round(disk.total / (1024**3), 1),
            "free_gb": round(disk.free / (1024**3), 1),
            "percent_used": disk.percent,
        }
        boot_time = datetime.fromtimestamp(psutil.boot_time()).isoformat()
    except ImportError:
        ram_info = {"error": "psutil not installed"}
        cpu_percent = 0
        disk_info = {"error": "psutil not installed"}
        boot_time = "unknown"

    node_v = _safe_run(["node", "--version"])
    python_v = sys.version.split()[0]

    return {
        "hostname": platform.node(),
        "platform": platform.platform(),
        "python_version": python_v,
        "node_version": node_v,
        "uptime": _now_iso(),
        "boot_time": boot_time if isinstance(boot_time, str) else "unknown",
        "ram": ram_info,
        "cpu_percent": cpu_percent,
        "disk": disk_info,
        "workspace": str(WORKSPACE),
        "freebuff_version": "2.0.0",
    }


@app.get("/api/tests")
async def get_test_results() -> dict[str, Any]:
    """Запускает pytest и возвращает сводку."""
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "tests_09/", "-v", "--tb=short"],
            capture_output=True, text=True, timeout=120,
        )
        output = r.stdout + r.stderr
        lines = output.split("\n")

        # Парсим итоговую строку
        summary = {"total": 0, "passed": 0, "failed": 0, "errors": 0, "warnings": 0}
        for line in lines:
            if "passed" in line and "failed" in line and "error" in line:
                parts = line.strip().split()
                for i, p in enumerate(parts):
                    if p == "passed":
                        try:
                            summary["passed"] = int(parts[i - 1])
                        except (ValueError, IndexError):
                            pass
                    elif p == "failed":
                        try:
                            summary["failed"] = int(parts[i - 1])
                        except (ValueError, IndexError):
                            pass
                    elif p == "error":
                        try:
                            summary["errors"] = int(parts[i - 1])
                        except (ValueError, IndexError):
                            pass
            if "warning" in line and "warnings" in line:
                parts = line.strip().split()
                for i, p in enumerate(parts):
                    if p == "warnings":
                        try:
                            summary["warnings"] = int(parts[i - 1])
                        except (ValueError, IndexError):
                            pass

        summary["total"] = summary["passed"] + summary["failed"] + summary["errors"]

        # Находим failed тесты
        failed_tests = []
        for line in lines:
            if line.strip().startswith("FAILED "):
                failed_tests.append(line.strip().replace("FAILED ", ""))

        # Разбивка по тестовым файлам
        file_breakdown: dict[str, dict[str, int]] = {}
        current_file = ""
        for line in lines:
            if line.startswith("tests_09/"):
                current_file = line.split("::")[0] if "::" in line else line.strip()[:-1]
                if current_file not in file_breakdown:
                    file_breakdown[current_file] = {"tests": 0, "passed": 0, "failed": 0}
            if current_file and ("PASSED" in line or "FAILED" in line or "ERROR" in line):
                if current_file in file_breakdown:
                    file_breakdown[current_file]["tests"] += 1
                    if "PASSED" in line:
                        file_breakdown[current_file]["passed"] += 1
                    elif "FAILED" in line or "ERROR" in line:
                        file_breakdown[current_file]["failed"] += 1

        return {
            "summary": summary,
            "failed_tests": failed_tests[:20],
            "file_breakdown": file_breakdown,
            "raw_output": output[-2000:] if len(output) > 2000 else output,
            "timestamp": _now_iso(),
        }
    except subprocess.TimeoutExpired:
        return {"error": "Tests timed out after 120s", "summary": {"total": 0, "passed": 0, "failed": 1, "errors": 0}}
    except Exception as e:
        return {"error": str(e), "summary": {"total": 0, "passed": 0, "failed": 1, "errors": 1}}


@app.get("/api/sessions")
async def list_sessions(limit: int = 20) -> dict[str, Any]:
    """Список сессий из ContextManager."""
    try:
        from scripts_01.context_manager import ContextManager, SessionStatus
        cm = ContextManager(str(WORKSPACE))
        sessions = cm.list_sessions()[:limit]

        # Сводка по статусам
        status_counts: dict[str, int] = {}
        for s in sessions:
            st = s.get("status", "unknown")
            status_counts[st] = status_counts.get(st, 0) + 1

        # Активные сессии
        active = [s for s in sessions if s.get("status") == SessionStatus.ACTIVE.value]

        return {
            "total": len(sessions),
            "status_counts": status_counts,
            "active_count": len(active),
            "sessions": [
                {
                    "id": s.get("session_id", "")[:12],
                    "session_id": s.get("session_id", "")[:12],
                    "project": s.get("project", ""),
                    "topic": s.get("topic", ""),
                    "status": s.get("status", ""),
                    "message_count": s.get("message_count", 0),
                    "token_estimate": s.get("token_estimate", 0),
                    "updated_at": s.get("updated_at", ""),
                }
                for s in sessions
            ],
        }
    except Exception as e:
        return {"error": str(e), "total": 0, "sessions": []}


@app.get("/api/sessions_15/{session_id)")
async def get_session_detail(session_id: str) -> dict[str, Any]:
    """Детали сессии: сообщения, чекпоинты."""
    try:
        from scripts_01.context_manager import ContextManager
        cm = ContextManager(str(WORKSPACE))

        session = cm.get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")

        messages = cm.get_messages(session_id, limit=50)
        checkpoints = cm.get_checkpoints(session_id)

        return {
            "session": {
                "id": session.session_id[:12],
                "project": session.project,
                "topic": session.topic,
                "status": session.status.value,
                "message_count": session.message_count,
                "token_estimate": session.token_estimate,
                "last_summary": session.last_summary[:500] if session.last_summary else "",
                "created_at": session.created_at,
                "updated_at": session.updated_at,
            },
            "messages": [
                {
                    "role": m.get("role", ""),
                    "content": m.get("content", "")[:500],
                    "token_count": m.get("token_count", 0),
                    "timestamp": m.get("timestamp", ""),
                }
                for m in messages[-20:]  # последние 20
            ],
            "checkpoints": [
                {
                    "type": cp.get("checkpoint_type", ""),
                    "summary": cp.get("summary", "")[:200],
                    "message_count": cp.get("message_count", 0),
                    "created_at": cp.get("created_at", ""),
                }
                for cp in checkpoints[-10:]
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions_15/{session_id)/messages")
async def get_session_messages(session_id: str, limit: int = 50) -> dict[str, Any]:
    """Сообщения сессии."""
    try:
        from scripts_01.context_manager import ContextManager
        cm = ContextManager(str(WORKSPACE))
        messages = cm.get_messages(session_id, limit=limit)
        return {
            "session_id": session_id[:12],
            "total": len(messages),
            "messages": [
                {
                    "role": m.get("role", ""),
                    "content": m.get("content", "")[:1000],
                    "token_count": m.get("token_count", 0),
                    "timestamp": m.get("timestamp", ""),
                }
                for m in messages
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/memory")
async def get_memory_stats() -> dict[str, Any]:
    """Статистика Memory Engine по всем уровням."""
    try:
        from scripts_01.memory_engine import MemoryEngine
        me = MemoryEngine(str(WORKSPACE))
        stats = me.get_stats()
        return stats
    except Exception as e:
        return {"error": str(e), "total": 0}


@app.get("/api/events")
async def get_recent_events(limit: int = 30) -> dict[str, Any]:
    """Последние события из EventBus."""
    try:
        from scripts_01.event_bus import EventBus
        bus = EventBus()
        events = bus.get_events(limit=limit)
        return {
            "total": len(events),
            "events": [
                {
                    "id": e.event_id[:8],
                    "type": e.event_type,
                    "source": e.source,
                    "timestamp": e.timestamp,
                    "delivered_to": e.delivered_to,
                }
                for e in events
            ],
        }
    except Exception as e:
        return {"error": str(e), "total": 0, "events": []}


@app.get("/api/events/stats")
async def get_event_stats() -> dict[str, Any]:
    """Статистика EventBus."""
    try:
        from scripts_01.event_bus import EventBus
        bus = EventBus()
        stats = bus.get_stats()
        return stats
    except Exception as e:
        return {"error": str(e), "total_events": 0, "active_subscribers": 0}


@app.get("/api/knowledge")
async def get_knowledge_stats() -> dict[str, Any]:
    """Статистика базы знаний (Knowledge Engine)."""
    try:
        from scripts_01.knowledge_engine import KnowledgeEngine
        ke = KnowledgeEngine(workspace_root=str(WORKSPACE))
        count = ke.count()
        return {
            "indexed_docs": count,
            "fts_enabled": True,
            "workspace": str(WORKSPACE),
        }
    except Exception as e:
        return {"error": str(e), "indexed_docs": 0}


@app.get("/api/git")
async def get_git_status() -> dict[str, Any]:
    """Git статус: ветка, изменения, последний коммит."""
    branch = _safe_run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    changes = _safe_run(["git", "status", "--porcelain"])
    last_commit = _safe_run(["git", "log", "--oneline", "-1"])
    total_commits = _safe_run(["git", "rev-list", "--count", "HEAD"])

    # Считаем changed files
    changed_files = []
    if changes and "error" not in changes:
        for line in changes.split("\n"):
            if line.strip():
                parts = line.strip().split(maxsplit=1)
                if len(parts) == 2:
                    changed_files.append({"status": parts[0], "file": parts[1]})

    return {
        "branch": branch,
        "last_commit": last_commit,
        "total_commits": total_commits,
        "changed_files_count": len(changed_files),
        "changed_files": changed_files[:20],
        "has_changes": len(changed_files) > 0,
    }


@app.get("/api/checkpoints")
async def get_recent_checkpoints(limit: int = 10) -> dict[str, Any]:
    """Последние чекпоинты из всех сессий."""
    try:
        from scripts_01.context_manager import ContextManager
        cm = ContextManager(str(WORKSPACE))
        sessions = cm.list_sessions()[:10]
        all_checkpoints = []

        for s in sessions:
            sid = s.get("session_id", "")
            if not sid:
                continue
            cps = cm.get_checkpoints(sid)
            for cp in cps:
                all_checkpoints.append({
                    "session_id": sid[:12],
                    "type": cp.get("checkpoint_type", ""),
                    "summary": cp.get("summary", "")[:150],
                    "message_count": cp.get("message_count", 0),
                    "created_at": cp.get("created_at", ""),
                })

        all_checkpoints.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return {"total": len(all_checkpoints), "checkpoints": all_checkpoints[:limit]}
    except Exception as e:
        return {"error": str(e), "total": 0, "checkpoints": []}


@app.get("/api/orchestrator")
async def get_orchestrator_status() -> dict[str, Any]:
    """Статус Orchestrator (сколько workflow запущено)."""
    return {
        "status": "active",
        "workflows": [],
        "total_workflows": 0,
        "active_workflows": 0,
    }


@app.get("/api")
async def api_root() -> dict[str, Any]:
    """Корень API — список всех эндпоинтов."""
    return {
        "name": "Buffy Dashboard API",
        "version": "1.0.0",
        "endpoints": [
            "/api/system",
            "/api/tests",
            "/api/sessions",
            "/api/sessions_15/{id]",
            "/api/sessions_15/{id]/messages",
            "/api/memory",
            "/api/events",
            "/api/events/stats",
            "/api/knowledge",
            "/api/git",
            "/api/checkpoints",
            "/api/orchestrator",
        ],
        "timestamp": _now_iso(),
    }


# ═══════════════════════════════════════════════════════════════
# Запуск
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    port = int(os.environ.get("DASHBOARD_PORT", "8080"))
    print(f"🚀 Buffy Dashboard API starting on http://0.0.0.0:{port}")
    print(f"   API docs: http://127.0.0.1:{port}/docs")
    print(f"   Workspace: {WORKSPACE}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
