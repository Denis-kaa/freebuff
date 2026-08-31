"""
Freebuff Plugin — MCP сервер.

Инструменты:
  start_session       — начать сессию (Python → выход, память свободна)
  log_message         — записать сообщение в стрим-сессию
  get_context         — получить конспект последней сессии
  get_status          — статус системы
  run_freebuff        — запустить Codebuff phase-based (анти-OOM)
  get_task_result     — проверить результат запущенной задачи
  end_session         — завершить сессию

Ресурсы:
  freebuff://session/current — текущая сессия
  freebuff://context_12/last    — последний конспект

Подключается через STDIO (для MCP клиентов).
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

FREEBUFF_ROOT = Path(os.environ.get(
    "FREEBUFF_ROOT",
    str(Path(__file__).resolve().parent.parent),
))
sys.path.insert(0, str(FREEBUFF_ROOT))

from freebuff_plugin_03 import bridge as plugin_bridge
from freebuff_plugin_03 import wrapper as plugin_wrapper
from freebuff_plugin_03.scenario_engine import ScenarioEngine
from freebuff_plugin_03.config import MCP_SERVER_NAME, MCP_SERVER_VERSION


class MCPServer:
    """MCP сервер через STDIO транспорт."""

    def __init__(self):
        self._session_id: str | None = None
        self._last_task_sid: str | None = None
        self._last_task_start: float | None = None
        self.request_id = 0
        self._scenario_engine = ScenarioEngine()

    # ── Event Store (ленивая инициализация) ────────────────

    _event_store = None

    def _get_event_store(self):
        if self._event_store is None:
            from freebuff_plugin_03.event.store import EventStore
            self._event_store = EventStore()
        return self._event_store

    # ── Event tools ──────────────────────────────────────────

    def _list_event_tools(self) -> list[dict]:
        return [
            {
                "name": "event_search",
                "description": "Поиск событий в Event Store по типу, сессии, тексту",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "event_type": {
                            "type": "string",
                            "description": "Фильтр по типу (task.*, audit.decision)",
                        },
                        "session_id": {"type": "string", "description": "Фильтр по сессии"},
                        "data_search": {"type": "string", "description": "Полнотекстовый поиск"},
                        "limit": {"type": "number", "default": 20},
                    },
                },
            },
            {
                "name": "event_timeline",
                "description": "Временная шкала событий проекта",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project": {"type": "string", "description": "Фильтр по проекту"},
                        "limit": {"type": "number", "default": 30},
                    },
                },
            },
            {
                "name": "event_replay",
                "description": "Воспроизвести события из Event Store",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "event_type": {"type": "string", "description": "Фильтр по типу"},
                        "session_id": {"type": "string", "description": "Фильтр по сессии"},
                        "speed": {
                            "type": "string",
                            "enum": ["instant", "realtime"],
                            "default": "instant",
                        },
                    },
                },
            },
            {
                "name": "event_audit",
                "description": "Аудит решений Policy Engine и действий пользователя",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "target_type": {
                            "type": "string",
                            "enum": ["decision", "action", "config_change"],
                            "description": "Тип аудита",
                        },
                        "limit": {"type": "number", "default": 20},
                    },
                },
            },
            {
                "name": "event_pulse",
                "description": "Лента активных событий проекта",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project": {"type": "string", "description": "Фильтр по проекту"},
                        "limit": {"type": "number", "default": 10},
                    },
                },
            },
        ]

    # ── Сценарии ────────────────────────────────────────────

    def _list_scenario_tools(self) -> list[dict]:
        return [
            {
                "name": "list_scenarios",
                "description": "Список доступных сценариев (готовых промтов) с фильтром по категории",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Фильтр: freelancing / agent / templates",
                        }
                    },
                },
            },
            {
                "name": "get_scenario",
                "description": "Детали одного сценария",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "slug": {"type": "string", "description": "ID сценария (напр. freelance_parser)"},
                    },
                    "required": ["slug"],
                },
            },
            {
                "name": "apply_scenario",
                "description": "Применить сценарий — получить готовый промт с подставленными переменными",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "slug": {"type": "string", "description": "ID сценария"},
                        "variables": {
                            "type": "object",
                            "description": "Переменные для подстановки, например: {\"URL\": \"https://...\"]",
                        },
                    },
                    "required": ["slug"],
                },
            },
            {
                "name": "search_scenarios",
                "description": "Поиск сценариев по тексту",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Поисковый запрос"},
                    },
                    "required": ["query"],
                },
            },
        ]

    # ── Инструменты ──────────────────────────────────────────

    def _list_tools(self) -> list[dict]:
        tools = [
            {
                "name": "start_session",
                "description": "Начать новую стрим-сессию с памятью",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "Тема сессии",
                        }
                    },
                    "required": ["topic"],
                },
            },
            {
                "name": "log_message",
                "description": "Записать сообщение в текущую стрим-сессию",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "role": {
                            "type": "string",
                            "enum": ["user", "assistant", "system"],
                        },
                        "content": {"type": "string"},
                        "session_id": {
                            "type": "string",
                            "description": "ID сессии (если не указан — последняя активная)",
                        },
                    },
                    "required": ["role", "content"],
                },
            },
            {
                "name": "get_context",
                "description": "Получить конспект последней завершённой сессии",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "get_status",
                "description": "Статус системы и активных задач",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "run_freebuff",
                "description": "Запустить Codebuff phase-based (Python не ждёт — анти-OOM)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string", "description": "Задача для freebuff"},
                        "topic": {"type": "string", "description": "Тема сессии"},
                        "timeout": {"type": "number", "description": "Таймаут в секундах"},
                    },
                    "required": ["task"],
                },
            },
            {
                "name": "get_task_result",
                "description": "Проверить результат запущенной задачи (по session_id)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "ID сессии из run_freebuff"}
                    },
                    "required": ["session_id"],
                },
            },
            {
                "name": "end_session",
                "description": "Завершить сессию с конспектом",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"}
                    },
                    "required": ["summary"],
                },
            },
        ]
        tools.extend(self._list_event_tools())
        tools.extend(self._list_scenario_tools())
        tools.extend(self._list_sync_tools())
        return tools

    def _list_sync_tools(self) -> list[dict]:
        return [
            {
                "name": "sync_status",
                "description": "Текущий статус remote-sync (idle/connected/conflict/quarantine) "
                               "для UI-индикатора + последние события",
                "inputSchema": {"type": "object", "properties": {}},
            },
        ]

    def _call_tool(self, name: str, arguments: dict) -> dict:
        try:
            if name == "start_session":
                topic = arguments.get("topic", "freebuff session")
                sid = plugin_bridge.session_start(topic)
                self._session_id = sid
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "session_id": sid,
                            "topic": topic,
                            "status": "started",
                        }, ensure_ascii=False),
                    }]
                }

            elif name == "log_message":
                role = arguments["role"]
                content = arguments["content"]
                sid = arguments.get("session_id", self._session_id)

                if sid:
                    # Пишем напрямую в raw.jsonl сессии
                    plugin_bridge._log_json(sid, role, {"content": content})
                    # И в conversation.log через StreamBridge
                    try:
                        bridge = plugin_bridge.get_stream_bridge()
                        if role == "user":
                            bridge.log_user(content)
                        elif role == "system":
                            bridge.log_system(content)
                        else:
                            bridge.log_assistant(content)
                    except Exception:
                        pass

                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "role": role,
                            "session_id": sid,
                            "status": "logged",
                        }, ensure_ascii=False),
                    }]
                }

            elif name == "get_context":
                bridge = plugin_bridge.get_stream_bridge()
                summary = bridge.get_context_resume()
                return {
                    "content": [{
                        "type": "text",
                        "text": summary or "Нет завершённых сессий",
                    }]
                }

            elif name == "get_status":
                active_pids = plugin_wrapper.list_active_pids()
                info = {
                    "session_active": self._session_id is not None,
                    "session_id": self._session_id,
                    "active_tasks": len(active_pids),
                    "tasks": active_pids,
                }
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(info, ensure_ascii=False),
                    }]
                }

            elif name == "run_freebuff":
                task = arguments["task"]
                topic = arguments.get("topic", task[:80])
                timeout = arguments.get("timeout", 300)

                # Phase-based launch — Python не ждёт Codebuff
                result = plugin_wrapper.launch(
                    prompt=task,
                    cwd=str(FREEBUFF_ROOT),
                    timeout=timeout,
                )

                self._last_task_sid = result.get("session_id", "")
                self._last_task_start = time.time()
                self._session_id = self._last_task_sid

                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(result, ensure_ascii=False, default=str),
                    }]
                }

            elif name == "get_task_result":
                sid = arguments.get("session_id", self._last_task_sid)
                if not sid:
                    return {
                        "content": [{"type": "text", "text": "Нет активных задач"}]
                    }

                # Проверяем PID-файл
                pid_info = plugin_wrapper.read_pid_file(sid)
                if pid_info is None:
                    # Задача завершена — проверяем конспект
                    bridge = plugin_bridge.get_stream_bridge()
                    conspect = bridge.get_context_resume()
                    return {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({
                                "session_id": sid,
                                "running": False,
                                "conspect": conspect,
                            }, ensure_ascii=False, default=str),
                        }]
                    }

                # Задача ещё выполняется
                alive = plugin_wrapper._is_pid_alive(pid_info["pid"])
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "session_id": sid,
                            "running": alive,
                            "pid": pid_info["pid"],
                            "cwd": pid_info["cwd"],
                        }, ensure_ascii=False),
                    }]
                }

            elif name == "end_session":
                summary = arguments.get("summary", "Session completed")
                if self._session_id:
                    cp = plugin_bridge.session_end(self._session_id, summary)
                    self._session_id = None
                else:
                    cp = None
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "status": "ended",
                            "conspect_path": str(cp) if cp else None,
                        }, ensure_ascii=False),
                    }]
                }

            elif name == "list_scenarios":
                category = arguments.get("category")
                scenarios = self._scenario_engine.list_scenarios(category=category)
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(scenarios, ensure_ascii=False, default=str),
                    }]
                }

            elif name == "get_scenario":
                slug = arguments.get("slug", "")
                scenario = self._scenario_engine.get_scenario(slug)
                if not scenario:
                    return {
                        "isError": True,
                        "content": [{"type": "text", "text": f"Scenario not found: {slug}"}],
                    }
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(scenario.to_dict(), ensure_ascii=False, default=str),
                    }]
                }

            elif name == "apply_scenario":
                slug = arguments.get("slug", "")
                variables = arguments.get("variables", {})
                result = self._scenario_engine.apply_scenario(slug, variables)
                if "error" in result:
                    return {
                        "isError": True,
                        "content": [{"type": "text", "text": result["error"]}],
                    }
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(result, ensure_ascii=False, default=str),
                    }]
                }

            elif name == "search_scenarios":
                query = arguments.get("query", "")
                results = self._scenario_engine.search_scenarios(query)
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(results, ensure_ascii=False, default=str),
                    }]
                }

            elif name == "event_search":
                store = self._get_event_store()
                from freebuff_plugin_03.event import EventQuery
                query = EventQuery(
                    event_type=arguments.get("event_type"),
                    session_id=arguments.get("session_id"),
                    data_search=arguments.get("data_search"),
                    limit=arguments.get("limit", 20),
                )
                entries = store.query(query)
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps([{
                            "id": e.event_id,
                            "type": e.event_type,
                            "source": e.source,
                            "data": e.data,
                            "timestamp": e.timestamp[:19],
                        } for e in entries], ensure_ascii=False, default=str),
                    }]
                }

            elif name == "event_timeline":
                store = self._get_event_store()
                from freebuff_plugin_03.event.timeline import TimelineEngine
                timeline = TimelineEngine(store)
                result = timeline.get_timeline(
                    project=arguments.get("project", ""),
                    limit=arguments.get("limit", 30),
                )
                return {
                    "content": [{
                        "type": "text",
                        "text": timeline.format_timeline_text(result),
                    }]
                }

            elif name == "event_replay":
                store = self._get_event_store()
                from freebuff_plugin_03.event import EventQuery
                from freebuff_plugin_03.event.replay import EventReplay
                replay = EventReplay(store)
                query = EventQuery(
                    event_type=arguments.get("event_type"),
                    session_id=arguments.get("session_id"),
                    limit=1000,
                )
                result = replay.replay(query, speed=arguments.get("speed", "instant"))
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "total": result.total_events,
                            "delivered": result.delivered,
                            "errors": result.errors,
                            "duration_ms": result.duration_ms,
                        }, ensure_ascii=False),
                    }]
                }

            elif name == "event_audit":
                store = self._get_event_store()
                from freebuff_plugin_03.event.audit import AuditEngine
                audit = AuditEngine(store)
                target_type = arguments.get("target_type", "")
                limit = arguments.get("limit", 20)
                trail = audit.get_audit_trail(target_type=target_type, limit=limit)
                text = audit.format_audit_log(trail)
                return {
                    "content": [{"type": "text", "text": text}]
                }

            elif name == "event_pulse":
                store = self._get_event_store()
                from freebuff_plugin_03.event.pulse import PulseEngine
                pulse = PulseEngine(bus=None, store=store)
                feed = pulse.get_pulse(
                    project=arguments.get("project", ""),
                    limit=arguments.get("limit", 10),
                )
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps([{
                            "icon": e.icon,
                            "title": e.title,
                            "description": e.description,
                            "timestamp": e.timestamp[:19],
                            "severity": e.severity,
                        } for e in feed], ensure_ascii=False),
                    }]
                }

            elif name == "sync_status":
                # Phase 5.4 — status snapshot for the Flutter UI indicator
                # (via MCP event stream). Reads the app-level active coordinator.
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
                # Recent remote_sync.* events from EventStore (the stream)
                try:
                    store = self._get_event_store()
                    from freebuff_plugin_03.event import EventQuery
                    entries = store.query(EventQuery(event_type="remote_sync.*", limit=10))
                    snapshot["recent_events"] = [{
                        "id": e.event_id,
                        "type": e.event_type,
                        "status": (e.data or {}).get("status"),
                        "timestamp": e.timestamp[:19],
                    } for e in entries]
                except Exception:
                    snapshot["recent_events"] = []
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(snapshot, ensure_ascii=False, default=str),
                    }]
                }

            else:
                return {
                    "isError": True,
                    "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
                }

        except Exception as e:
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"Error: {e}"}],
            }

    # ── Ресурсы ──────────────────────────────────────────────

    def _list_resources(self) -> list[dict]:
        return [
            {
                "uri": "freebuff://session/current",
                "name": "Текущая сессия",
                "description": "Информация о текущей активной сессии",
                "mimeType": "application/json",
            },
            {
                "uri": "freebuff://context_12/last",
                "name": "Последний конспект",
                "description": "Конспект последней завершённой сессии",
                "mimeType": "text/markdown",
            },
        ]

    def _read_resource(self, uri: str) -> str | None:
        if uri == "freebuff://session/current":
            return json.dumps({
                "active": self._session_id is not None,
                "session_id": self._session_id,
            }, ensure_ascii=False)
        elif uri == "freebuff://context_12/last":
            bridge = plugin_bridge.get_stream_bridge()
            return bridge.get_context_resume() or "Нет данных"
        return None

    # ── STDIO loop ───────────────────────────────────────────

    def _send(self, msg: dict) -> None:
        line = json.dumps(msg, ensure_ascii=False)
        sys.stdout.write(f"Content-Length: {len(line.encode('utf-8'))}\r\n\r\n{line}")
        sys.stdout.flush()

    def _recv(self) -> dict | None:
        length = 0
        while True:
            header = sys.stdin.readline()
            if not header:
                return None
            header = header.strip()
            if header.startswith("Content-Length:"):
                length = int(header.split(":")[1].strip())
            elif not header:
                break
        if length <= 0:
            return None
        body = sys.stdin.read(length)
        return json.loads(body) if body else None

    def run_stdio(self) -> None:
        """Главный цикл MCP сервера."""
        while True:
            try:
                msg = self._recv()
                if msg is None:
                    break

                msg_id = msg.get("id")
                method = msg.get("method", "")
                params = msg.get("params", {})

                if method == "initialize":
                    self._send({
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {"tools": {}, "resources": {}},
                            "serverInfo": {
                                "name": MCP_SERVER_NAME,
                                "version": MCP_SERVER_VERSION,
                            },
                        },
                    })
                elif method == "notifications/initialized":
                    pass
                elif method == "tools/list":
                    self._send({
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {"tools": self._list_tools()},
                    })
                elif method == "tools/call":
                    result = self._call_tool(
                        params.get("name", ""),
                        params.get("arguments", {}),
                    )
                    self._send({
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": result,
                    })
                elif method == "resources/list":
                    self._send({
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {"resources": self._list_resources()},
                    })
                elif method == "resources/read":
                    uri = params.get("uri", "")
                    content = self._read_resource(uri)
                    if content is not None:
                        self._send({
                            "jsonrpc": "2.0",
                            "id": msg_id,
                            "result": {
                                "contents": [{"uri": uri, "mimeType": "text/markdown", "text": content}]
                            },
                        })
                    else:
                        self._send({
                            "jsonrpc": "2.0",
                            "id": msg_id,
                            "error": {"code": -32000, "message": f"Resource not found: {uri}"},
                        })
                else:
                    self._send({
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "error": {"code": -32601, "message": f"Method not found: {method}"},
                    })

            except json.JSONDecodeError:
                continue
            except EOFError:
                break
            except KeyboardInterrupt:
                break
            except Exception as e:
                try:
                    self._send({
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32000, "message": str(e)},
                    })
                except Exception:
                    pass


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Freebuff Plugin MCP Server")
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio")
    parser.add_argument("--port", type=int, default=8411)

    args = parser.parse_args()
    server = MCPServer()

    if args.transport == "stdio":
        server.run_stdio()
    else:
        try:
            from flask import Flask, request, Response, jsonify
            import queue

            app = Flask(__name__)
            message_queue: queue.Queue = queue.Queue()

            @app.route("/")
            def index():
                return "Freebuff Plugin MCP Server — running"

            @app.route("/sse", methods=["GET"])
            def sse():
                def event_stream():
                    while True:
                        msg = message_queue.get()
                        yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                return Response(event_stream(), mimetype="text/event-stream")

            @app.route("/message", methods=["POST"])
            def message():
                data = request.json
                message_queue.put(data)
                return jsonify({"ok": True})

            print(f"MCP SSE Server on :{args.port}")
            app.run(host="127.0.0.1", port=args.port, debug=False)
        except ImportError:
            print("Flask not available. Install: pip install flask")
            sys.exit(1)


if __name__ == "__main__":
    main()
