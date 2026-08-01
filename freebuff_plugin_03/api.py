"""
Freebuff Plugin — FastAPI REST сервер.

Эндпоинты:
  POST /chat          — отправить запрос (роутинг: Qwen ↔ freebuff)
  POST /session       — управление сессиями
  GET  /status        — статус системы
  POST /freebuff/run  — запустить freebuff phase-based (анти-OOM)
  GET  /context       — последний конспект
  GET  /tasks         — список активных задач

Использование:
    uvicorn freebuff_plugin.api:app --host 127.0.0.1 --port 8410
"""

from __future__ import annotations

import os
import sys
***REMOVED***
from typing import Any

FREEBUFF_ROOT = Path(os.environ.get(
    "FREEBUFF_ROOT",
    str(Path(__file__).resolve().parent.parent),
))
sys.path.insert(0, str(FREEBUFF_ROOT))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from freebuff_plugin import bridge as plugin_bridge
from freebuff_plugin import wrapper as plugin_wrapper
from freebuff_plugin_03.router import IntentRouter
from freebuff_plugin_03.scenario_engine import ScenarioEngine

# ── Приложение ────────────────────────────────────────────────

app = FastAPI(
    title="Freebuff Plugin API",
    version="0.1.0",
    description="REST API для плагина freebuff: контекстная память + роутинг + запуск freebuff",
)

# Stateless — каждый вызов создаёт новую сессию через bridge
router = IntentRouter()


# ── Модели ────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    topic: str | None = None
    force_freebuff: bool = False

class ChatResponse(BaseModel):
    session_id: str
    routed_to: str
    response: str
    duration: float

class SessionStartRequest(BaseModel):
    topic: str = "api session"

class SessionEndRequest(BaseModel):
    summary: str = "API session completed"

class FreebuffRunRequest(BaseModel):
    task: str
    topic: str | None = None
    timeout: int = 300

class FreebuffRunResponse(BaseModel):
    session_id: str
    success: bool
    pid: int | None = None
    status: str = "launched"
    message: str = ""


# ── Эндпоинты ─────────────────────────────────────────────────

@app.get("/status")
async def get_status() -> dict:
    """Статус плагина и активных задач."""
    active_pids = plugin_wrapper.list_active_pids()
    return {
        "plugin": "freebuff-plugin",
        "version": "0.1.0",
        "active_tasks": len(active_pids),
        "tasks": active_pids,
        "freebuff_binary_exists": plugin_wrapper.FREEBUFF_BINARY.exists(),
    ***REMOVED***


@app.post("/chat")
async def chat(req: ChatRequest) -> ChatResponse:
    """
    Принять запрос, решить кому направить.

    Простые запросы → локальный ответ (через router).
    Сложные → phase-based запуск freebuff.
    """
    import time
    t0 = time.time()

    decision = router.route(req.message)

    if decision["target"***REMOVED*** == "freebuff" or req.force_freebuff:
        # Phase-based запуск freebuff
        sid = plugin_bridge.session_start(topic=req.topic or req.message[:80***REMOVED***)
        plugin_bridge._log_json(sid, "user", {"content": req.message***REMOVED***)

        result = plugin_wrapper.launch(
            prompt=req.message,
            cwd=str(FREEBUFF_ROOT),
            timeout=300,
            session_id=sid,
        )
        duration = time.time() - t0

        return ChatResponse(
            session_id=result.get("session_id", "?"),
            routed_to="freebuff",
            response=f"Задача запущена (session: {result.get('session_id', '?')***REMOVED***, PID: {result.get('pid', '?')***REMOVED***)\n"
                     f"Статус: {result.get('status', '?')***REMOVED***\n"
                     f"Проверить: GET /status",
            duration=round(duration, 1),
        )
    else:
        # Локальный ответ (Qwen 0.5B)
        local_response = router.local_response(req.message)
        duration = time.time() - t0
        return ChatResponse(
            session_id="local",
            routed_to="local_qwen",
            response=local_response,
            duration=round(duration, 1),
        )


@app.post("/session")
async def session(action: str = "start", topic: str = "api session", summary: str = "Session completed") -> dict:
    """Управление сессиями: start / end."""
    if action == "start":
        sid = plugin_bridge.session_start(topic=topic)
        return {"status": "started", "session_id": sid***REMOVED***
    elif action == "end":
        sessions = plugin_bridge.session_list()
        if sessions:
            sid = sessions[-1***REMOVED***["session_id"***REMOVED***[:8***REMOVED***
            cp = plugin_bridge.session_end(sid, summary)
            return {"status": "ended", "session_id": sid, "conspect_path": str(cp) if cp else None***REMOVED***
        return {"status": "no_active_sessions"***REMOVED***
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action***REMOVED***")


@app.post("/freebuff/run")
async def freebuff_run(req: FreebuffRunRequest) -> FreebuffRunResponse:
    """Запустить freebuff phase-based (анти-OOM)."""
    sid = plugin_bridge.session_start(topic=req.topic or req.task[:80***REMOVED***)
    plugin_bridge._log_json(sid, "user", {"content": req.task***REMOVED***)

    result = plugin_wrapper.launch(
        prompt=req.task,
        cwd=str(FREEBUFF_ROOT),
        timeout=req.timeout,
        session_id=sid,
    )

    return FreebuffRunResponse(
        session_id=result.get("session_id", sid),
        success=result.get("success", False),
        pid=result.get("pid"),
        status=result.get("status", "error"),
        message=result.get("message", ""),
    )


@app.get("/context")
async def get_context() -> dict:
    """Последний конспект."""
    bridge = plugin_bridge.get_stream_bridge()
    conspect = bridge.get_context_resume()
    return {"conspect": conspect, "has_conspect": bool(conspect)***REMOVED***


@app.get("/tasks")
async def list_tasks() -> list[dict***REMOVED***:
    """Список активных задач."""
    return plugin_wrapper.list_active_pids()


# ── Scenario Engine ────────────────────────────────────────────

_scenario_engine = ScenarioEngine()


@app.get("/scenarios")
async def list_scenarios(category: str | None = None, tag: str | None = None):
    """Список доступных сценариев."""
    return {
        "scenarios": _scenario_engine.list_scenarios(category=category, tag=tag),
        "total": len(_scenario_engine.list_scenarios(category=category, tag=tag)),
    ***REMOVED***


@app.get("/scenarios/search")
async def search_scenarios(q: str = ""):
    """Поиск сценариев."""
    return {"results": _scenario_engine.search_scenarios(q)***REMOVED***


@app.get("/scenarios/{slug***REMOVED***")
async def get_scenario(slug: str):
    """Детали сценария."""
    scenario = _scenario_engine.get_scenario(slug)
    if not scenario:
        raise HTTPException(status_code=404, detail=f"Scenario not found: {slug***REMOVED***")
    return scenario.to_dict()


class ScenarioApplyRequest(BaseModel):
    variables: dict[str, str***REMOVED*** | None = None


@app.post("/scenarios/{slug***REMOVED***/apply")
async def apply_scenario(slug: str, req: ScenarioApplyRequest):
    """Применить сценарий — получить готовый промт."""
    result = _scenario_engine.apply_scenario(slug, req.variables)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"***REMOVED***)


# ── Запуск ────────────────────────────────────────────────────

def main():
    import uvicorn
    from freebuff_plugin_03.config import API_HOST, API_PORT

    print(f"🚀 Freebuff Plugin API: http://{API_HOST***REMOVED***:{API_PORT***REMOVED***")
    print(f"   Документация: http://{API_HOST***REMOVED***:{API_PORT***REMOVED***/docs")
    uvicorn.run(app, host=API_HOST, port=API_PORT)


if __name__ == "__main__":
    main()
