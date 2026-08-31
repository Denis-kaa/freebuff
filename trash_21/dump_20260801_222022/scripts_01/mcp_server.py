#!/usr/bin/env python3
"""
mcp_server.py — MCP Server для Buffy Project.

Model Context Protocol server на чистом Python (без внешних SDK).
Транспорт: stdio (JSON-RPC 2.0 over stdin/stdout) и Streamable HTTP
(single endpoint /mcp: POST для запросов, GET для SSE stream, DELETE для session).

Design decision: pure Python без официального `mcp` SDK, т.к. пакет не установлен
на Termux (ModuleNotFoundError). MCP протокол — это JSON-RPC 2.0, поэтому
реализация на stdlib + asyncio достаточна и портативна.
Существующий phone_mcp_server.py использует официальный SDK; этот сервер —
нет, для независимости от внешних зависимостей.

Экспонирует возможности Buffy внешним AI-агентам:
  - Tools:    ToolRegistry (git, file, shell, sqlite, http) + knowledge/memory/context
  - Resources: BUFFY.md, ROADMAP.md, knowledge entries, memory entries, session info
  - Prompts:  context_resume, knowledge_search, task_start

Интеграция с Claude / Gemini / OpenClaw:
  Claude config (claude_desktop_config.json) — stdio:
    {
      "mcpServers": {
        "buffy": {
          "command": "python",
          "args": ["/path/to/freebuff/scripts_01/mcp_server.py"]
        }
      }
    }

  HTTP (Streamable HTTP transport):
    python scripts_01/mcp_server.py --http --port 8765
    Endpoint: http://127.0.0.1:8765/mcp
    POST: JSON-RPC, GET: SSE stream, DELETE: session

  OpenClaw / Gemini: stdio или HTTP transport.

Использование:
    python scripts_01/mcp_server.py                    # stdio режим
    python scripts_01/mcp_server.py --http             # HTTP режим (port 8765)
    python scripts_01/mcp_server.py --tools            # список MCP tools
    python scripts_01/mcp_server.py --resources        # список MCP resources
    python scripts_01/mcp_server.py --call knowledge_search '{"query": "router"]'
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import threading
import traceback
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from queue import Queue, Empty
from typing import Any, Callable, Dict, List, Optional, Tuple

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))


# ═══════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════

PROTOCOL_VERSION = "2025-03-26"
SERVER_NAME = "buffy-mcp-server"
SERVER_VERSION = "1.0.0"

# JSON-RPC error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


# ═══════════════════════════════════════════════════════════════
# Types
# ═══════════════════════════════════════════════════════════════


@dataclass
class McpTool:
    """MCP tool definition."""
    name: str
    description: str
    input_schema: Dict[str, Any] = field(default_factory=lambda: {"type": "object", "properties": {}})
    handler: Optional[Callable] = None
    category: str = "general"


@dataclass
class McpResource:
    """MCP resource definition."""
    uri: str
    name: str
    description: str
    mime_type: str = "text/plain"
    handler: Optional[Callable] = None


@dataclass
class McpPrompt:
    """MCP prompt template."""
    name: str
    description: str
    arguments: List[Dict[str, Any]] = field(default_factory=list)
    handler: Optional[Callable] = None


# ═══════════════════════════════════════════════════════════════
# JSON-RPC helpers
# ═══════════════════════════════════════════════════════════════


def rpc_response(req_id: Any, result: Any) -> str:
    """Создаёт JSON-RPC success response."""
    return json.dumps({
        "jsonrpc": "2.0",
        "id": req_id,
        "result": result,
    }, ensure_ascii=False)


def rpc_error(req_id: Any, code: int, message: str, data: Any = None) -> str:
    """Создаёт JSON-RPC error response."""
    err: Dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return json.dumps({
        "jsonrpc": "2.0",
        "id": req_id,
        "error": err,
    }, ensure_ascii=False)


def rpc_notification(method: str, params: Dict[str, Any]) -> str:
    """Создаёт JSON-RPC notification (no id, no response expected)."""
    return json.dumps({
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
    }, ensure_ascii=False)


# ═══════════════════════════════════════════════════════════════
# Session Management (Streamable HTTP)
# ═══════════════════════════════════════════════════════════════


@dataclass
class McpSession:
    """MCP HTTP session with notification queue for SSE.

    Note: No automatic TTL/cleanup — sessions persist until DELETE.
    If a client crashes without DELETE, the session remains in memory.
    For production use, add a periodic cleanup thread or max-age check.
    """

    session_id: str
    notification_queue: Queue = field(default_factory=Queue)
    active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class McpSessionManager:
    """Thread-safe session manager for Streamable HTTP transport."""

    def __init__(self):
        self._sessions: Dict[str, McpSession] = {}
        self._lock = threading.Lock()

    def create_session(self) -> str:
        """Create a new session and return its ID."""
        session_id = str(uuid.uuid4())
        with self._lock:
            self._sessions[session_id] = McpSession(session_id)
        return session_id

    def get_session(self, session_id: str) -> Optional[McpSession]:
        """Get a session by ID."""
        with self._lock:
            return self._sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        """Delete a session. Returns True if found and deleted."""
        with self._lock:
            session = self._sessions.pop(session_id, None)
            if session:
                session.active = False
                return True
            return False

    def push_notification(self, session_id: str, message: str) -> bool:
        """Push a notification to a session's SSE stream."""
        session = self.get_session(session_id)
        if session and session.active:
            session.notification_queue.put(message)
            return True
        return False

    def count(self) -> int:
        """Return number of active sessions."""
        with self._lock:
            return len(self._sessions)


# ═══════════════════════════════════════════════════════════════
# BuffyMcpServer
# ═══════════════════════════════════════════════════════════════


class BuffyMcpServer:
    """MCP Server для Buffy Project.

    Экспонирует:
      - ToolRegistry инструменты как MCP tools
      - Knowledge Engine как MCP resource + tool
      - Memory Engine как MCP resource + tool
      - ContextManager как MCP resource + tool
      - Документы (BUFFY.md, ROADMAP.md) как MCP resources
      - Prompts для context_resume и task_start

    Особенности:
      - Pure Python, без внешних MCP SDK
      - JSON-RPC 2.0 over stdio
      - Lazy loading компонентов (импортируются при первом использовании)
      - EventBus интеграция (mcp.* events)
    """

    def __init__(self, workspace_root: str | Path | None = None):
        self.workspace = Path(workspace_root) if workspace_root else WORKSPACE
        self._tools: Dict[str, McpTool] = {}
        self._resources: Dict[str, McpResource] = {}
        self._prompts: Dict[str, McpPrompt] = {}
        self._initialized = False
        self._client_info: Dict[str, Any] = {}

        # Lazy-loaded components
        self._tool_registry = None
        self._knowledge_engine = None
        self._memory_engine = None
        self._context_manager = None
        self._event_bus = None
        self._bridge_layer = None
        self._bootstrap_engine = None
        self._runtime_registry = None
        self._runtime_capability_registry = None
        self._policy_engine = None

        # Phase 7 (CoWork) lazy-loaded components — восстановленные модули
        self._roles_engine = None
        self._presence_engine = None
        self._collaboration_engine = None
        self._distributed_coordinator = None
        self._rag_engine = None
        self._project_pulse = None
        self._event_store = None

        # Register all MCP capabilities
        self._register_tools()
        self._register_phase7_tools()
        self._register_event_tools()
        self._register_resources()
        self._register_prompts()

    # ── Lazy component accessors ───────────────────────────

    def _get_tool_registry(self):
        if self._tool_registry is None:
            from scripts_01.tool_runtime import (
                ToolRegistry, GitTool, SQLiteTool, HTTPTool, FileTool, ShellTool,
            )
            self._tool_registry = ToolRegistry(
                event_bus=self._get_event_bus(),
                default_context={"workspace": str(self.workspace)},
            )
            for cls in [GitTool, SQLiteTool, HTTPTool, FileTool, ShellTool]:
                self._tool_registry.register(cls())
        return self._tool_registry

    def _get_knowledge_engine(self):
        if self._knowledge_engine is None:
            from scripts_01.knowledge_engine import KnowledgeEngine
            self._knowledge_engine = KnowledgeEngine(workspace_root=str(self.workspace))
        return self._knowledge_engine

    def _get_memory_engine(self):
        if self._memory_engine is None:
            from scripts_01.memory_engine import MemoryEngine
            self._memory_engine = MemoryEngine(
                workspace_root=str(self.workspace),
                event_bus=self._get_event_bus(),
            )
        return self._memory_engine

    def _get_context_manager(self):
        if self._context_manager is None:
            from scripts_01.context_manager import ContextManager
            self._context_manager = ContextManager(str(self.workspace))
        return self._context_manager

    def _get_event_bus(self):
        if self._event_bus is None:
            try:
                from scripts_01.event_bus import get_default_event_bus
                self._event_bus = get_default_event_bus(str(self.workspace))
            except Exception:
                pass  # EventBus optional
        return self._event_bus

    def _get_bridge_layer(self):
        """Lazy-load Bridge Layer with graceful degradation."""
        if self._bridge_layer is None:
            try:
                from freebuff_plugin_03 import BridgeLayer
                bus = self._get_event_bus()
                self._bridge_layer = BridgeLayer(
                    event_bus=bus or None,
                    agent_name="buffy-mcp",
                    agent_version="1.0.0",
                )
                self._bridge_layer.start()
            except ImportError as e:
                print(f"⚠️ MCP: BridgeLayer unavailable (plugin not loaded): {e}", file=sys.stderr)
                return None
            except Exception as e:
                print(f"⚠️ MCP: BridgeLayer init failed: {e}", file=sys.stderr)
                return None
        return self._bridge_layer

    def _get_bootstrap_engine(self):
        """Lazy-load Bootstrap Engine with graceful degradation."""
        if self._bootstrap_engine is None:
            try:
                from freebuff_plugin_03 import BootstrapEngine
                bus = self._get_event_bus()
                self._bootstrap_engine = BootstrapEngine(
                    workspace_root=str(self.workspace),
                    event_bus=bus or None,
                )
            except ImportError as e:
                print(f"⚠️ MCP: BootstrapEngine unavailable (plugin not loaded): {e}", file=sys.stderr)
                return None
            except Exception as e:
                print(f"⚠️ MCP: BootstrapEngine init failed: {e}", file=sys.stderr)
                return None
        return self._bootstrap_engine

    def _get_runtime_registry(self):
        """Lazy-load Runtime Registry with graceful degradation."""
        if self._runtime_registry is None:
            try:
                from freebuff_plugin_03 import RuntimeRegistry, RuntimeCapabilityRegistry
                storage = self.workspace / "data_13" / "runtime_registry.json"
                self._runtime_registry = RuntimeRegistry(storage_path=storage)
                self._runtime_registry.load()
                self._runtime_capability_registry = RuntimeCapabilityRegistry(self._runtime_registry)
            except ImportError as e:
                print(f"⚠️ MCP: RuntimeRegistry unavailable (plugin not loaded): {e}", file=sys.stderr)
                return None
            except Exception as e:
                print(f"⚠️ MCP: RuntimeRegistry init failed: {e}", file=sys.stderr)
                return None
        return self._runtime_registry

    def _get_policy_engine(self):
        """Lazy-load Policy Engine for capability-based runtime selection."""
        if self._policy_engine is None:
            try:
                from freebuff_plugin_03.policy import PolicyEngine
                registry = self._get_runtime_registry()
                cap_reg = self._runtime_capability_registry
                if registry is None or cap_reg is None:
                    return None
                self._policy_engine = PolicyEngine(registry, cap_reg)
            except ImportError as e:
                print(f"⚠️ MCP: PolicyEngine unavailable (plugin not loaded): {e}", file=sys.stderr)
                return None
            except Exception as e:
                print(f"⚠️ MCP: PolicyEngine init failed: {e}", file=sys.stderr)
                return None
        return self._policy_engine

    def _publish(self, event_type: str, data: Dict[str, Any]) -> None:
        """Publish MCP event to EventBus."""
        bus = self._get_event_bus()
        if bus is None:
            return
        try:
            from scripts_01.event_bus import Event
            bus.publish(Event(
                type=f"mcp.{event_type}",
                source="mcp_server",
                data=data,
            ))
        except Exception:
            pass

    # ── Phase 7 (CoWork) accessors ────────────────────────────────────

    def _get_roles_engine(self):
        """Lazy-load RoleEngine with graceful degradation."""
        if self._roles_engine is None:
            try:
                from scripts_01.roles import RoleEngine

                self._roles_engine = RoleEngine()
            except Exception as e:
                print(f"⚠️ MCP: RoleEngine init failed: {e}", file=sys.stderr)
                return None
        return self._roles_engine

    def _get_presence_engine(self):
        """Lazy-load PresenceEngine with graceful degradation."""
        if self._presence_engine is None:
            try:
                from scripts_01.presence import PresenceEngine

                self._presence_engine = PresenceEngine()
            except Exception as e:
                print(f"⚠️ MCP: PresenceEngine init failed: {e}", file=sys.stderr)
                return None
        return self._presence_engine

    def _get_collaboration_engine(self):
        """Lazy-load CollaborationEngine with graceful degradation."""
        if self._collaboration_engine is None:
            try:
                from scripts_01.collaboration import CollaborationEngine

                self._collaboration_engine = CollaborationEngine(
                    event_bus=self._get_event_bus(),
                )
            except Exception as e:
                print(f"⚠️ MCP: CollaborationEngine init failed: {e}", file=sys.stderr)
                return None
        return self._collaboration_engine

    def _get_distributed_coordinator(self):
        """Lazy-load DistributedCoordinator with graceful degradation."""
        if self._distributed_coordinator is None:
            try:
                from scripts_01.distributed_agents import DistributedCoordinator

                self._distributed_coordinator = DistributedCoordinator(
                    event_bus=self._get_event_bus(),
                )
            except Exception as e:
                print(f"⚠️ MCP: DistributedCoordinator init failed: {e}", file=sys.stderr)
                return None
        return self._distributed_coordinator

    def _get_rag_engine(self):
        """Lazy-load RAGEngine with graceful degradation."""
        if self._rag_engine is None:
            try:
                from scripts_01.rag_engine import RAGEngine

                self._rag_engine = RAGEngine(workspace_root=str(self.workspace))
            except Exception as e:
                print(f"⚠️ MCP: RAGEngine init failed: {e}", file=sys.stderr)
                return None
        return self._rag_engine

    def _get_project_pulse(self):
        """Lazy-load ProjectPulse with graceful degradation."""
        if self._project_pulse is None:
            try:
                from scripts_01.project_pulse import ProjectPulse

                self._project_pulse = ProjectPulse(
                    workspace=self.workspace,
                    event_bus=self._get_event_bus(),
                )
            except Exception as e:
                print(f"⚠️ MCP: ProjectPulse init failed: {e}", file=sys.stderr)
                return None
        return self._project_pulse

    def _get_event_store(self):
        """Lazy-load Event Store (freebuff_plugin_03.event) with graceful degradation."""
        if self._event_store is None:
            try:
                from freebuff_plugin_03.event.store import EventStore

                self._event_store = EventStore(db_path=self.workspace / "context_12" / "events.db")
            except ImportError as e:
                print(f"⚠️ MCP: EventStore unavailable (plugin not loaded): {e}", file=sys.stderr)
                return None
            except Exception as e:
                print(f"⚠️ MCP: EventStore init failed: {e}", file=sys.stderr)
                return None
        return self._event_store

    # ── Phase 7 (CoWork) tool registration ────────────────────────────

    def _register_phase7_tools(self) -> None:
        """Регистрирует MCP tools восстановленных Phase 7 модулей."""
        # ── Roles ──
        self._tools["roles_list"] = McpTool(
            name="roles_list",
            description="List role definitions and assignments (RoleEngine).",
            input_schema={"type": "object", "properties": {"definitions": {"type": "boolean", "description": "Show role definitions", "default": False}}},
            handler=self._handle_roles_list,
            category="roles",
        )
        self._tools["roles_get"] = McpTool(
            name="roles_get",
            description="Get roles assigned to an agent.",
            input_schema={"type": "object", "properties": {"agent": {"type": "string", "description": "Agent name"}}, "required": ["agent"]},
            handler=self._handle_roles_get,
            category="roles",
        )
        self._tools["roles_assign"] = McpTool(
            name="roles_assign",
            description="Assign a role to an agent.",
            input_schema={"type": "object", "properties": {"agent": {"type": "string"}, "role": {"type": "string"}}, "required": ["agent", "role"]},
            handler=self._handle_roles_assign,
            category="roles",
        )
        self._tools["roles_unassign"] = McpTool(
            name="roles_unassign",
            description="Remove a role from an agent.",
            input_schema={"type": "object", "properties": {"agent": {"type": "string"}, "role": {"type": "string"}}, "required": ["agent", "role"]},
            handler=self._handle_roles_unassign,
            category="roles",
        )
        self._tools["roles_stats"] = McpTool(
            name="roles_stats",
            description="Role engine statistics.",
            input_schema={"type": "object", "properties": {}},
            handler=self._handle_roles_stats,
            category="roles",
        )

        # ── Presence ──
        self._tools["presence_list"] = McpTool(
            name="presence_list",
            description="List registered agents with optional status/capability filters.",
            input_schema={"type": "object", "properties": {"status": {"type": "string"}, "capability": {"type": "string"}}},
            handler=self._handle_presence_list,
            category="presence",
        )
        self._tools["presence_get"] = McpTool(
            name="presence_get",
            description="Get presence details of a single agent.",
            input_schema={"type": "object", "properties": {"agent": {"type": "string", "description": "Agent name"}}, "required": ["agent"]},
            handler=self._handle_presence_get,
            category="presence",
        )
        self._tools["presence_history"] = McpTool(
            name="presence_history",
            description="Get presence status-change history.",
            input_schema={"type": "object", "properties": {"agent": {"type": "string", "description": "Agent name"}, "limit": {"type": "integer", "default": 50}}},
            handler=self._handle_presence_history,
            category="presence",
        )

        # ── Collaboration ──
        self._tools["collab_create"] = McpTool(
            name="collab_create",
            description="Create a collaboration session.",
            input_schema={"type": "object", "properties": {"topic": {"type": "string"}, "owner": {"type": "string"}, "participants": {"type": "array", "items": {"type": "string"}}}, "required": ["topic", "owner"]},
            handler=self._handle_collab_create,
            category="collaboration",
        )
        self._tools["collab_list"] = McpTool(
            name="collab_list",
            description="List collaboration sessions.",
            input_schema={"type": "object", "properties": {"status": {"type": "string"}}},
            handler=self._handle_collab_list,
            category="collaboration",
        )
        self._tools["collab_get"] = McpTool(
            name="collab_get",
            description="Get collaboration session details.",
            input_schema={"type": "object", "properties": {"session_id": {"type": "string"}}, "required": ["session_id"]},
            handler=self._handle_collab_get,
            category="collaboration",
        )
        self._tools["collab_join"] = McpTool(
            name="collab_join",
            description="Join a collaboration session.",
            input_schema={"type": "object", "properties": {"session_id": {"type": "string"}, "participant": {"type": "string"}, "role": {"type": "string"}}, "required": ["session_id", "participant"]},
            handler=self._handle_collab_join,
            category="collaboration",
        )
        self._tools["collab_leave"] = McpTool(
            name="collab_leave",
            description="Leave a collaboration session.",
            input_schema={"type": "object", "properties": {"session_id": {"type": "string"}, "participant": {"type": "string"}}, "required": ["session_id", "participant"]},
            handler=self._handle_collab_leave,
            category="collaboration",
        )
        self._tools["collab_send"] = McpTool(
            name="collab_send",
            description="Send a message to a collaboration session.",
            input_schema={"type": "object", "properties": {"session_id": {"type": "string"}, "sender": {"type": "string"}, "content": {"type": "string"}, "msg_type": {"type": "string", "default": "text"}}, "required": ["session_id", "sender", "content"]},
            handler=self._handle_collab_send,
            category="collaboration",
        )
        self._tools["collab_history"] = McpTool(
            name="collab_history",
            description="Get message history of a session.",
            input_schema={"type": "object", "properties": {"session_id": {"type": "string"}, "limit": {"type": "integer", "default": 50}}, "required": ["session_id"]},
            handler=self._handle_collab_history,
            category="collaboration",
        )
        self._tools["collab_status"] = McpTool(
            name="collab_status",
            description="Collaboration engine diagnostics.",
            input_schema={"type": "object", "properties": {}},
            handler=self._handle_collab_status,
            category="collaboration",
        )

        # ── Distributed Agents ──
        self._tools["distributed_list"] = McpTool(
            name="distributed_list",
            description="List distributed agent mesh and coordinator status.",
            input_schema={"type": "object", "properties": {}},
            handler=self._handle_distributed_list,
            category="distributed",
        )
        self._tools["distributed_spawn"] = McpTool(
            name="distributed_spawn",
            description="Spawn/register a distributed agent.",
            input_schema={"type": "object", "properties": {"name": {"type": "string"}, "command": {"type": "string"}, "capabilities": {"type": "object"}}},
            handler=self._handle_distributed_spawn,
            category="distributed",
        )
        self._tools["distributed_run"] = McpTool(
            name="distributed_run",
            description="Run a distributed workflow plan.",
            input_schema={"type": "object", "properties": {"goal": {"type": "string"}, "steps": {"type": "array", "items": {"type": "object"}}}, "required": ["goal", "steps"]},
            handler=self._handle_distributed_run,
            category="distributed",
        )
        self._tools["distributed_status"] = McpTool(
            name="distributed_status",
            description="Distributed system status.",
            input_schema={"type": "object", "properties": {}},
            handler=self._handle_distributed_status,
            category="distributed",
        )
        self._tools["distributed_broadcast"] = McpTool(
            name="distributed_broadcast",
            description="Broadcast a message to all distributed agents.",
            input_schema={"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]},
            handler=self._handle_distributed_broadcast,
            category="distributed",
        )

        # ── RAG ──
        self._tools["rag_search"] = McpTool(
            name="rag_search",
            description="RAG 2.0 semantic search with ranking.",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}, "top_k": {"type": "integer", "default": 10}, "mode": {"type": "string", "default": "hybrid_rrf"}}, "required": ["query"]},
            handler=self._handle_rag_search,
            category="rag",
        )
        self._tools["rag_hybrid"] = McpTool(
            name="rag_hybrid",
            description="Quick hybrid RRF search.",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}, "top_k": {"type": "integer", "default": 10}}, "required": ["query"]},
            handler=self._handle_rag_hybrid,
            category="rag",
        )
        self._tools["rag_rerank"] = McpTool(
            name="rag_rerank",
            description="Feature-based re-ranking of candidates.",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}, "top_k": {"type": "integer", "default": 10}}, "required": ["query"]},
            handler=self._handle_rag_rerank,
            category="rag",
        )

        # ── Project Pulse ──
        self._tools["pulse_list"] = McpTool(
            name="pulse_list",
            description="List project pulse entries.",
            input_schema={"type": "object", "properties": {"limit": {"type": "integer", "default": 50}, "event_type": {"type": "string"}, "source": {"type": "string"}}},
            handler=self._handle_pulse_list,
            category="pulse",
        )
        self._tools["pulse_stats"] = McpTool(
            name="pulse_stats",
            description="Project pulse statistics.",
            input_schema={"type": "object", "properties": {}},
            handler=self._handle_pulse_stats,
            category="pulse",
        )
        self._tools["pulse_scan"] = McpTool(
            name="pulse_scan",
            description="Run full project scan (git + files) into the pulse.",
            input_schema={"type": "object", "properties": {}},
            handler=self._handle_pulse_scan,
            category="pulse",
        )

    # ── Event Platform tools (EVENT_PLATFORM_SPECIFICATION §9) ────────

    def _register_event_tools(self) -> None:
        """Регистрирует MCP tools Event Platform (event_search/timeline/replay/audit/pulse)."""
        self._tools["event_search"] = McpTool(
            name="event_search",
            description="Поиск событий в Event Store по типу, сессии, тексту.",
            input_schema={
                "type": "object",
                "properties": {
                    "event_type": {"type": "string", "description": "Фильтр по типу (task.*, audit.decision)"},
                    "session_id": {"type": "string", "description": "Фильтр по сессии"},
                    "data_search": {"type": "string", "description": "Полнотекстовый поиск"},
                    "limit": {"type": "integer", "description": "Max results", "default": 20},
                },
            },
            handler=self._handle_event_search,
            category="event",
        )
        self._tools["event_timeline"] = McpTool(
            name="event_timeline",
            description="Временная шкала событий проекта.",
            input_schema={
                "type": "object",
                "properties": {
                    "project": {"type": "string", "description": "Фильтр по проекту"},
                    "limit": {"type": "integer", "description": "Max entries", "default": 30},
                },
            },
            handler=self._handle_event_timeline,
            category="event",
        )
        self._tools["event_replay"] = McpTool(
            name="event_replay",
            description="Воспроизвести события из Event Store (для восстановления состояния).",
            input_schema={
                "type": "object",
                "properties": {
                    "event_type": {"type": "string", "description": "Фильтр по типу"},
                    "session_id": {"type": "string", "description": "Фильтр по сессии"},
                    "speed": {"type": "string", "enum": ["instant", "realtime"], "default": "instant"},
                },
            },
            handler=self._handle_event_replay,
            category="event",
        )
        self._tools["event_audit"] = McpTool(
            name="event_audit",
            description="Аудит решений Policy Engine и действий пользователя.",
            input_schema={
                "type": "object",
                "properties": {
                    "target_type": {"type": "string", "enum": ["decision", "action", "config_change"], "description": "Тип аудита"},
                    "limit": {"type": "integer", "description": "Max entries", "default": 20},
                },
            },
            handler=self._handle_event_audit,
            category="event",
        )
        self._tools["event_pulse"] = McpTool(
            name="event_pulse",
            description="Лента активных событий проекта.",
            input_schema={
                "type": "object",
                "properties": {
                    "project": {"type": "string", "description": "Фильтр по проекту"},
                    "limit": {"type": "integer", "description": "Max entries", "default": 10},
                },
            },
            handler=self._handle_event_pulse,
            category="event",
        )

    # ── Phase 7 handlers: Roles ───────────────────────────────────────

    def _handle_roles_list(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List role definitions and assignments."""
        engine = self._get_roles_engine()
        if engine is None:
            return {"success": False, "error": "RoleEngine not available"}
        try:
            data = {
                "roles": [r.to_dict() for r in engine.list_roles()],
                "assignments": [a.to_dict() for a in engine.list_assignments()],
            }
            self._publish("roles.listed", {"roles": len(data["roles"]), "assignments": len(data["assignments"])})
            return {"success": True, "data": data}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_roles_get(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get roles of an agent."""
        engine = self._get_roles_engine()
        if engine is None:
            return {"success": False, "error": "RoleEngine not available"}
        agent = arguments.get("agent", "")
        if not agent:
            return {"success": False, "error": "Missing required parameter: agent"}
        try:
            return {"success": True, "data": {"agent": agent, "roles": engine.get_roles(agent)}}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_roles_assign(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Assign a role to an agent."""
        engine = self._get_roles_engine()
        if engine is None:
            return {"success": False, "error": "RoleEngine not available"}
        agent = arguments.get("agent", "")
        role = arguments.get("role", "")
        if not agent or not role:
            return {"success": False, "error": "Missing required parameters: agent, role"}
        try:
            ok = engine.assign_role(agent, role)
            if not ok:
                return {"success": False, "error": f"Unknown role: {role}"}
            return {"success": True, "data": {"agent": agent, "role": role}}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_roles_unassign(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Remove a role from an agent."""
        engine = self._get_roles_engine()
        if engine is None:
            return {"success": False, "error": "RoleEngine not available"}
        agent = arguments.get("agent", "")
        role = arguments.get("role", "")
        if not agent or not role:
            return {"success": False, "error": "Missing required parameters: agent, role"}
        try:
            ok = engine.unassign_role(agent, role)
            return {"success": True, "data": {"agent": agent, "role": role, "removed": ok}}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_roles_stats(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Role engine statistics."""
        engine = self._get_roles_engine()
        if engine is None:
            return {"success": False, "error": "RoleEngine not available"}
        try:
            return {"success": True, "data": engine.get_stats()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Phase 7 handlers: Presence ────────────────────────────────────

    def _handle_presence_list(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List agents with filters."""
        engine = self._get_presence_engine()
        if engine is None:
            return {"success": False, "error": "PresenceEngine not available"}
        try:
            data = engine.list_agents_json(
                status=arguments.get("status"), capability=arguments.get("capability")
            )
            self._publish("presence.listed", {"total": data.get("total", 0)})
            return {"success": True, "data": data}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_presence_get(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get agent presence details."""
        engine = self._get_presence_engine()
        if engine is None:
            return {"success": False, "error": "PresenceEngine not available"}
        agent_name = arguments.get("agent") or arguments.get("agent_name", "")
        if not agent_name:
            return {"success": False, "error": "agent is required"}
        try:
            return {"success": True, "data": engine.get_agent_json(agent_name)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_presence_history(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get presence history."""
        engine = self._get_presence_engine()
        if engine is None:
            return {"success": False, "error": "PresenceEngine not available"}
        try:
            return {"success": True, "data": engine.get_history_json(
                agent_name=arguments.get("agent") or arguments.get("agent_name"),
                limit=int(arguments.get("limit", 50)),
            )}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Phase 7 handlers: Collaboration ───────────────────────────────

    def _handle_collab_create(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Create a collaboration session."""
        engine = self._get_collaboration_engine()
        if engine is None:
            return {"success": False, "error": "CollaborationEngine not available"}
        topic = arguments.get("topic", "")
        owner = arguments.get("owner", "")
        if not topic or not owner:
            return {"success": False, "error": "Missing required parameters: topic, owner"}
        try:
            session = engine.create_session(topic, owner, arguments.get("participants"))
            return {"success": True, "data": session.to_dict()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_collab_list(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List collaboration sessions."""
        engine = self._get_collaboration_engine()
        if engine is None:
            return {"success": False, "error": "CollaborationEngine not available"}
        try:
            sessions = engine.list_sessions(status=arguments.get("status"))
            return {"success": True, "data": {"sessions": [s.to_dict() for s in sessions]}}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_collab_get(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get session details."""
        engine = self._get_collaboration_engine()
        if engine is None:
            return {"success": False, "error": "CollaborationEngine not available"}
        session_id = arguments.get("session_id", "")
        if not session_id:
            return {"success": False, "error": "Missing required parameter: session_id"}
        try:
            session = engine.get_session(session_id)
            if session is None:
                return {"success": False, "error": f"Session not found: {session_id}"}
            return {"success": True, "data": session.to_dict()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_collab_join(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Join a session."""
        engine = self._get_collaboration_engine()
        if engine is None:
            return {"success": False, "error": "CollaborationEngine not available"}
        session_id = arguments.get("session_id", "")
        participant = arguments.get("participant", "")
        if not session_id or not participant:
            return {"success": False, "error": "Missing required parameters: session_id, participant"}
        try:
            ok = engine.join_session(session_id, participant, arguments.get("role", "editor"))
            return {"success": True, "data": {"joined": ok, "session_id": session_id, "participant": participant}}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_collab_leave(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Leave a session."""
        engine = self._get_collaboration_engine()
        if engine is None:
            return {"success": False, "error": "CollaborationEngine not available"}
        session_id = arguments.get("session_id", "")
        participant = arguments.get("participant", "")
        if not session_id or not participant:
            return {"success": False, "error": "Missing required parameters: session_id, participant"}
        try:
            ok = engine.leave_session(session_id, participant)
            return {"success": True, "data": {"left": ok}}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_collab_send(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Send a message to a session."""
        engine = self._get_collaboration_engine()
        if engine is None:
            return {"success": False, "error": "CollaborationEngine not available"}
        session_id = arguments.get("session_id", "")
        sender = arguments.get("sender", "")
        content = arguments.get("content", "")
        if not session_id or not sender or not content:
            return {"success": False, "error": "Missing required parameters: session_id, sender, content"}
        try:
            msg = engine.send_message(session_id, sender, content, arguments.get("msg_type", "text"))
            if msg is None:
                return {"success": False, "error": "Session not found or closed"}
            return {"success": True, "data": asdict(msg)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_collab_history(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get session history."""
        engine = self._get_collaboration_engine()
        if engine is None:
            return {"success": False, "error": "CollaborationEngine not available"}
        session_id = arguments.get("session_id", "")
        if not session_id:
            return {"success": False, "error": "Missing required parameter: session_id"}
        try:
            messages = engine.get_history(session_id, limit=int(arguments.get("limit", 50)))
            return {"success": True, "data": {"messages": [asdict(m) for m in messages]}}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_collab_status(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Collaboration engine diagnostics."""
        engine = self._get_collaboration_engine()
        if engine is None:
            return {"success": False, "error": "CollaborationEngine not available"}
        try:
            return {"success": True, "data": engine.get_status()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Phase 7 handlers: Distributed ─────────────────────────────────

    def _handle_distributed_list(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List distributed mesh."""
        coord = self._get_distributed_coordinator()
        if coord is None:
            return {"success": False, "error": "DistributedCoordinator not available"}
        try:
            agents = coord.list_agents()
            # total берём из mesh.get_summary() (контракт теста с mock-координатором).
            try:
                mesh_summary = coord.mesh.get_summary()
                total = int(mesh_summary.get("total", len(agents))) if isinstance(mesh_summary, dict) else len(agents)
            except Exception:
                total = len(agents)
            data = {"agents": agents, "total": total, "status": coord.get_status()}
            self._publish("distributed.listed", {"agents": total})
            return {"success": True, "data": data}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_distributed_spawn(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Spawn a distributed agent."""
        coord = self._get_distributed_coordinator()
        if coord is None:
            return {"success": False, "error": "DistributedCoordinator not available"}
        try:
            result = coord.spawn_agent(
                name=arguments.get("name"),
                command=arguments.get("command", "python"),
                capabilities=arguments.get("capabilities"),
            )
            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_distributed_run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Run a distributed workflow."""
        coord = self._get_distributed_coordinator()
        if coord is None:
            return {"success": False, "error": "DistributedCoordinator not available"}
        goal = arguments.get("goal", "")
        steps = arguments.get("steps")
        if not goal or not steps:
            return {"success": False, "error": "Missing required parameters: goal, steps"}
        try:
            plan = coord.run_distributed_workflow(goal=goal, steps=steps)
            return {"success": True, "data": plan.to_dict()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_distributed_status(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Distributed system status."""
        coord = self._get_distributed_coordinator()
        if coord is None:
            return {"success": False, "error": "DistributedCoordinator not available"}
        try:
            return {"success": True, "data": coord.get_status()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_distributed_broadcast(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Broadcast to all agents."""
        coord = self._get_distributed_coordinator()
        if coord is None:
            return {"success": False, "error": "DistributedCoordinator not available"}
        message = arguments.get("message", "")
        if not message:
            return {"success": False, "error": "Missing required parameter: message"}
        try:
            recipients = coord.broadcast_to_all(message, arguments.get("data"))
            return {"success": True, "data": {"recipients": recipients, "agents_notified": recipients, "message": message}}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Phase 7 handlers: RAG ─────────────────────────────────────────

    def _handle_rag_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """RAG search."""
        rag = self._get_rag_engine()
        if rag is None:
            return {"success": False, "error": "RAGEngine not available"}
        query = arguments.get("query", "")
        if not query:
            return {"success": False, "error": "Missing required parameter: query"}
        try:
            report = rag.search(
                query,
                top_k=int(arguments.get("top_k", 10)),
                mode=arguments.get("mode", "hybrid_rrf"),
            )
            return {"success": True, "data": report.to_dict()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_rag_hybrid(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Hybrid RRF search."""
        rag = self._get_rag_engine()
        if rag is None:
            return {"success": False, "error": "RAGEngine not available"}
        query = arguments.get("query", "")
        if not query:
            return {"success": False, "error": "Missing required parameter: query"}
        try:
            report = rag.hybrid_search(query, top_k=int(arguments.get("top_k", 10)))
            return {"success": True, "data": report.to_dict()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_rag_rerank(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Re-rank candidates."""
        rag = self._get_rag_engine()
        if rag is None:
            return {"success": False, "error": "RAGEngine not available"}
        query = arguments.get("query", "")
        if not query:
            return {"success": False, "error": "Missing required parameter: query"}
        try:
            report = rag.search(query, top_k=int(arguments.get("top_k", 30)) * 3, mode="hybrid_rrf", rerank_results=False)
            reranked = rag.rerank(query, report.results)
            return {"success": True, "data": [r.to_dict() for r in reranked[: int(arguments.get("top_k", 10))]]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Phase 7 handlers: Project Pulse ───────────────────────────────

    def _handle_pulse_list(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List pulse entries."""
        pulse = self._get_project_pulse()
        if pulse is None:
            return {"success": False, "error": "ProjectPulse not available"}
        try:
            data = pulse.list_json(
                limit=int(arguments.get("limit", 50)),
                event_type=arguments.get("event_type"),
                source=arguments.get("source"),
            )
            return {"success": True, "data": data}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_pulse_stats(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Pulse statistics."""
        pulse = self._get_project_pulse()
        if pulse is None:
            return {"success": False, "error": "ProjectPulse not available"}
        try:
            return {"success": True, "data": pulse.get_stats()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_pulse_scan(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Run full project scan."""
        pulse = self._get_project_pulse()
        if pulse is None:
            return {"success": False, "error": "ProjectPulse not available"}
        try:
            return {"success": True, "data": pulse.full_scan()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Event Platform handlers ───────────────────────────────────────

    def _handle_event_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Поиск событий в Event Store."""
        store = self._get_event_store()
        if store is None:
            return {"success": False, "error": "EventStore not available"}
        try:
            from freebuff_plugin_03.event import EventQuery
            query = EventQuery(
                event_type=arguments.get("event_type"),
                session_id=arguments.get("session_id"),
                data_search=arguments.get("data_search"),
                limit=int(arguments.get("limit", 20)),
            )
            entries = store.query(query)
            data = [{
                "id": e.event_id,
                "type": e.event_type,
                "source": e.source,
                "data": e.data,
                "timestamp": e.timestamp[:19],
            } for e in entries]
            self._publish("event.searched", {"total": len(data)})
            return {"success": True, "data": data}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_event_timeline(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Временная шкала событий проекта."""
        store = self._get_event_store()
        if store is None:
            return {"success": False, "error": "EventStore not available"}
        try:
            from freebuff_plugin_03.event.timeline import TimelineEngine
            timeline = TimelineEngine(store)
            result = timeline.get_timeline(
                project=arguments.get("project", ""),
                limit=int(arguments.get("limit", 30)),
            )
            return {
                "success": True,
                "data": {
                    "text": timeline.format_timeline_text(result),
                    "entries": [
                        {"timestamp": e.timestamp, "event_type": e.event_type, "icon": e.icon, "title": e.title}
                        for e in result.entries
                    ],
                    "total": result.total,
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_event_replay(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Воспроизвести события из Event Store."""
        store = self._get_event_store()
        if store is None:
            return {"success": False, "error": "EventStore not available"}
        try:
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
                "success": True,
                "data": {
                    "total": result.total_events,
                    "delivered": result.delivered,
                    "errors": result.errors,
                    "duration_ms": result.duration_ms,
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_event_audit(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Аудит решений и действий."""
        store = self._get_event_store()
        if store is None:
            return {"success": False, "error": "EventStore not available"}
        try:
            from freebuff_plugin_03.event.audit import AuditEngine
            audit = AuditEngine(store)
            trail = audit.get_audit_trail(
                target_type=arguments.get("target_type", ""),
                limit=int(arguments.get("limit", 20)),
            )
            return {
                "success": True,
                "data": {
                    "text": audit.format_audit_log(trail),
                    "entries": [
                        {"id": e.id, "type": e.type, "timestamp": e.timestamp, "data": e.data}
                        for e in trail
                    ],
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_event_pulse(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Лента событий проекта."""
        store = self._get_event_store()
        if store is None:
            return {"success": False, "error": "EventStore not available"}
        try:
            from freebuff_plugin_03.event.pulse import PulseEngine
            pulse = PulseEngine(bus=None, store=store)
            feed = pulse.get_pulse(
                project=arguments.get("project", ""),
                limit=int(arguments.get("limit", 10)),
            )
            return {
                "success": True,
                "data": [{
                    "icon": e.icon,
                    "title": e.title,
                    "description": e.description,
                    "timestamp": e.timestamp[:19],
                    "severity": e.severity,
                } for e in feed],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Tool registration ──────────────────────────────────

    def _register_tools(self) -> None:
        """Регистрирует все MCP tools."""
        # 1. ToolRegistry tools (auto-discovered)
        self._register_toolregistry_tools()

        # 2. Knowledge tools
        self._tools["knowledge_search"] = McpTool(
            name="knowledge_search",
            description="Search the Knowledge Engine (FTS5 + TF-IDF + semantic). Returns ranked results with snippets.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "mode": {"type": "string", "description": "Search mode: keyword, semantic, hybrid", "default": "hybrid"},
                    "top_k": {"type": "integer", "description": "Max results", "default": 10},
                },
                "required": ["query"],
            },
            handler=self._handle_knowledge_search,
            category="knowledge",
        )

        # 3. Memory tools
        self._tools["memory_store"] = McpTool(
            name="memory_store",
            description="Store a memory entry in Buffy's Memory Engine (5 levels: working, project, knowledge, personal, archive).",
            input_schema={
                "type": "object",
                "properties": {
                    "level": {"type": "string", "description": "Memory level", "enum": ["working", "project", "knowledge", "personal", "archive"]},
                    "key": {"type": "string", "description": "Memory key (unique within level)"},
                    "content": {"type": "string", "description": "Content to store"},
                    "summary": {"type": "string", "description": "Short summary", "default": ""},
                },
                "required": ["level", "key", "content"],
            },
            handler=self._handle_memory_store,
            category="memory",
        )

        self._tools["memory_retrieve"] = McpTool(
            name="memory_retrieve",
            description="Retrieve a memory entry from Buffy's Memory Engine by level and key.",
            input_schema={
                "type": "object",
                "properties": {
                    "level": {"type": "string", "description": "Memory level", "enum": ["working", "project", "knowledge", "personal", "archive"]},
                    "key": {"type": "string", "description": "Memory key"},
                },
                "required": ["level", "key"],
            },
            handler=self._handle_memory_retrieve,
            category="memory",
        )

        self._tools["memory_list"] = McpTool(
            name="memory_list",
            description="List all memory entries at a given level.",
            input_schema={
                "type": "object",
                "properties": {
                    "level": {"type": "string", "description": "Memory level", "enum": ["working", "project", "knowledge", "personal", "archive"]},
                },
                "required": ["level"],
            },
            handler=self._handle_memory_list,
            category="memory",
        )

        # 4. Context/Session tools
        self._tools["session_status"] = McpTool(
            name="session_status",
            description="Get the status of the current/last Buffy session (messages, tokens, context usage).",
            input_schema={"type": "object", "properties": {}},
            handler=self._handle_session_status,
            category="context",
        )

        self._tools["context_resume"] = McpTool(
            name="context_resume",
            description="Get the last session conspect for context restoration. Returns markdown summary of previous session.",
            input_schema={"type": "object", "properties": {}},
            handler=self._handle_context_resume,
            category="context",
        )

        # 5. Plugin tools
        self._tools["plugins_list"] = McpTool(
            name="plugins_list",
            description="List all loaded plugins and their states.",
            input_schema={"type": "object", "properties": {}},
            handler=self._handle_plugins_list,
            category="plugins",
        )

        # 6. Bridge Layer tools (Phase 6: CoWork/Companion)
        self._tools["bridge_connect"] = McpTool(
            name="bridge_connect",
            description="Connect to an external MCP server via stdio or HTTP. The server's tools become available as ACP capabilities.",
            input_schema={
                "type": "object",
                "properties": {
                    "transport": {
                        "type": "string",
                        "description": "Transport type",
                        "enum": ["stdio", "http"],
                    },
                    "command": {
                        "type": "string",
                        "description": "Command for stdio transport (e.g., 'python')",
                    },
                    "args": {
                        "type": "string",
                        "description": "Space-separated args for stdio (e.g., 'scripts_01/mcp_server.py')",
                    },
                    "endpoint": {
                        "type": "string",
                        "description": "HTTP endpoint (e.g., 'http://127.0.0.1:8765/mcp')",
                    },
                    "name": {
                        "type": "string",
                        "description": "Optional custom name for the server",
                    },
                },
                "required": ["transport"],
            },
            handler=self._handle_bridge_connect,
            category="bridge",
        )

        self._tools["bridge_list"] = McpTool(
            name="bridge_list",
            description="List all connected MCP servers and their available tools.",
            input_schema={"type": "object", "properties": {}},
            handler=self._handle_bridge_list,
            category="bridge",
        )

        self._tools["bridge_disconnect"] = McpTool(
            name="bridge_disconnect",
            description="Disconnect a connected MCP server by name.",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Server name to disconnect (from bridge_list)",
                    },
                },
                "required": ["name"],
            },
            handler=self._handle_bridge_disconnect,
            category="bridge",
        )

        self._tools["bridge_rpc"] = McpTool(
            name="bridge_rpc",
            description="Send a JSON-RPC request to a connected MCP server (e.g., tools/call, resources/list, ping).",
            input_schema={
                "type": "object",
                "properties": {
                    "server": {
                        "type": "string",
                        "description": "Server name (from bridge_list)",
                    },
                    "method": {
                        "type": "string",
                        "description": "MCP JSON-RPC method (tools/list, resources/list, tools/call, ping)",
                    },
                    "tool": {
                        "type": "string",
                        "description": "Tool name for tools/call",
                    },
                    "arguments": {
                        "type": "string",
                        "description": "JSON arguments for tools/call",
                    },
                },
                "required": ["server", "method"],
            },
            handler=self._handle_bridge_rpc,
            category="bridge",
        )

        # 7. Bootstrap Engine tools
        self._tools["bootstrap_check"] = McpTool(
            name="bootstrap_check",
            description="Check the current environment state (OS, Python, Node, Git, Disk, RAM, packages). Returns detailed environment report.",
            input_schema={
                "type": "object",
                "properties": {
                    "quick": {
                        "type": "boolean",
                        "description": "Quick check (OS, Python, Git, Disk only)",
                        "default": False,
                    },
                },
            },
            handler=self._handle_bootstrap_check,
            category="bootstrap",
        )

        self._tools["bootstrap_run"] = McpTool(
            name="bootstrap_run",
            description="Run full bootstrap: check environment → load profile → install components → diagnose → report. Idempotent — skips already-installed components.",
            input_schema={
                "type": "object",
                "properties": {
                    "profile": {
                        "type": "string",
                        "description": "Profile name: minimal, developer, offline, cloud, android",
                        "default": "minimal",
                    },
                },
            },
            handler=self._handle_bootstrap_run,
            category="bootstrap",
        )

        self._tools["bootstrap_status"] = McpTool(
            name="bootstrap_status",
            description="Get Bootstrap Engine status — whether bootstrap was ever run, last profile, warnings, errors.",
            input_schema={"type": "object", "properties": {}},
            handler=self._handle_bootstrap_status,
            category="bootstrap",
        )

        # 8. Runtime Abstraction Layer tools
        self._tools["runtime_list"] = McpTool(
            name="runtime_list",
            description="List all discovered AI runtimes, their connection status, capabilities, and the active runtime.",
            input_schema={"type": "object", "properties": {}},
            handler=self._handle_runtime_list,
            category="runtime",
        )

        self._tools["runtime_connect"] = McpTool(
            name="runtime_connect",
            description="Connect to a registered AI runtime by name (e.g., freebuff, claude-code). Performs MCP handshake.",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Runtime name to connect",
                    },
                },
                "required": ["name"],
            },
            handler=self._handle_runtime_connect,
            category="runtime",
        )

        self._tools["runtime_disconnect"] = McpTool(
            name="runtime_disconnect",
            description="Disconnect an active AI runtime by name.",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Runtime name to disconnect",
                    },
                },
                "required": ["name"],
            },
            handler=self._handle_runtime_disconnect,
            category="runtime",
        )

        self._tools["runtime_select"] = McpTool(
            name="runtime_select",
            description="Select the active default AI runtime by name.",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Runtime name to set as active",
                    },
                },
                "required": ["name"],
            },
            handler=self._handle_runtime_select,
            category="runtime",
        )

        self._tools["runtime_generate"] = McpTool(
            name="runtime_generate",
            description="Generate a response from an AI runtime. Selects runtime by capability, explicit name, or active runtime.",
            input_schema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Single prompt/message to send",
                    },
                    "messages": {
                        "type": "array",
                        "description": "Optional list of {role, content] messages (overrides prompt)",
                    },
                    "name": {
                        "type": "string",
                        "description": "Explicit runtime name (optional)",
                    },
                    "capability": {
                        "type": "string",
                        "description": "Select runtime by capability, e.g. coding (optional)",
                    },
                    "system": {
                        "type": "string",
                        "description": "System prompt (optional)",
                    },
                    "temperature": {
                        "type": "number",
                        "description": "Generation temperature",
                        "default": 0.7,
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum tokens to generate",
                    },
                },
            },
            handler=self._handle_runtime_generate,
            category="runtime",
        )

        # Правило 11 (User-Choice Override): диалоговое переопределение «используй X вместо Y»
        self._tools["policy_override"] = McpTool(
            name="policy_override",
            description=(
                "Apply conversational user override (правило 11): parse a natural-language "
                "phrase like 'use deepseek instead of claude for coding' and set a policy "
                "preference (runtime → capability). Persists to policies.json and affects "
                "subsequent runtime/model selection via model_gateway / orchestrator."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Natural-language override phrase, e.g. \"use deepseek instead of claude for coding\", \"используй freebuff для research\", \"switch coding to claude-code\"",
                    },
                },
                "required": ["message"],
            },
            handler=self._handle_policy_override,
            category="policy",
        )

    def _register_toolregistry_tools(self) -> None:
        """Auto-discover and register ToolRegistry tools as MCP tools."""
        try:
            registry = self._get_tool_registry()
            for tool_info in registry.list_tools():
                # Convert ToolRegistry params to JSON Schema
                properties: Dict[str, Any] = {}
                required: List[str] = []
                for p in tool_info.get("parameters", []):
                    prop: Dict[str, Any] = {"type": p["type"], "description": p["description"]}
                    if p.get("default") is not None:
                        prop["default"] = p["default"]
                    if p.get("enum"):
                        prop["enum"] = p["enum"]
                    properties[p["name"]] = prop
                    if p.get("required"):
                        required.append(p["name"])

                schema: Dict[str, Any] = {
                    "type": "object",
                    "properties": properties,
                }
                if required:
                    schema["required"] = required

                tool_name = tool_info["name"]
                self._tools[tool_name] = McpTool(
                    name=tool_name,
                    description=tool_info["description"],
                    input_schema=schema,
                    handler=self._make_toolregistry_handler(tool_name),
                    category=tool_info.get("category", "general"),
                )
        except Exception as e:
            print(f"⚠️ MCP: ToolRegistry discovery failed: {e}", file=sys.stderr)

    def _make_toolregistry_handler(self, tool_name: str) -> Callable:
        """Creates a handler that delegates to ToolRegistry.execute()."""
        def handler(arguments: Dict[str, Any]) -> Dict[str, Any]:
            registry = self._get_tool_registry()
            result = registry.execute(tool_name, arguments)
            self._publish("tool.called", {"tool": tool_name, "success": result.success})
            return {
                "success": result.success,
                "data": result.data,
                "error": result.error,
                "duration_ms": result.duration_ms,
            }
        return handler

    # ── Resource registration ──────────────────────────────

    def _register_resources(self) -> None:
        """Регистрирует все MCP resources."""
        # 1. Project documents
        doc_resources = [
            ("buffy://manifest", "buffy_manifest", "BUFFY.md — master prompt / agent manifesto", "BUFFY.md"),
            ("buffy://roadmap", "buffy_roadmap", "ROADMAP.md — project roadmap with 5 phases", "docs_10/vision/ROADMAP.md"),
            ("buffy://spec", "buffy_spec", "SPEC.md — technical specification", "SPEC.md"),
            ("buffy://changelog", "buffy_changelog", "CHANGELOG.md — version history", "CHANGELOG.md"),
            ("buffy://task", "buffy_task", "TASK.md — current task", "TASK.md"),
            ("buffy://inventory", "buffy_inventory", "SYSTEM_INVENTORY.md — full component catalog", "docs_10/core/SYSTEM_INVENTORY.md"),
            ("buffy://decisions", "buffy_decisions", "DECISIONS.md — index of architecture decision records", "docs_10/decisions/DECISIONS.md"),
        ]
        for uri, name, desc, rel_path in doc_resources:
            self._resources[uri] = McpResource(
                uri=uri,
                name=name,
                description=desc,
                mime_type="text/markdown",
                handler=self._make_file_resource_handler(rel_path),
            )

        # 2. Dynamic resources (knowledge, memory) — handled via URI patterns
        self._resources["buffy://knowledge"] = McpResource(
            uri="buffy://knowledge",
            name="knowledge_index",
            description="Knowledge Engine index — use knowledge_search tool to query, or buffy://knowledge/{key] to read specific entry",
            mime_type="application/json",
            handler=self._handle_knowledge_resource,
        )

        self._resources["buffy://memory"] = McpResource(
            uri="buffy://memory",
            name="memory_overview",
            description="Memory Engine overview — use buffy://memory/{level]/{key] to read specific entry",
            mime_type="application/json",
            handler=self._handle_memory_resource,
        )

    def _make_file_resource_handler(self, rel_path: str) -> Callable:
        """Creates a handler that reads a project file."""
        def handler(uri: str) -> Tuple[str, str]:
            full_path = self.workspace / rel_path
            if not full_path.exists():
                return "", f"File not found: {rel_path}"
            content = full_path.read_text(encoding="utf-8")
            return content, "text/markdown"
        return handler

    def _handle_knowledge_resource(self, uri: str) -> Tuple[str, str]:
        """Handle buffy://knowledge or buffy://knowledge/{key]."""
        parts = uri.replace("buffy://knowledge", "").strip("/").split("/", 1)
        if not parts or parts[0] == "":
            # List all knowledge entries
            from scripts_01.memory_engine import MemoryLevel
            me = self._get_memory_engine()
            entries = me.list_entries(MemoryLevel.KNOWLEDGE)
            data = [{"key": e.key, "summary": e.summary[:100]} for e in entries]
            return json.dumps(data, ensure_ascii=False, indent=2), "application/json"
        else:
            key = parts[0]
            from scripts_01.memory_engine import MemoryLevel
            me = self._get_memory_engine()
            entry = me.retrieve(MemoryLevel.KNOWLEDGE, key)
            if entry is None:
                return "", f"Knowledge entry not found: {key}"
            return entry.content, "text/markdown"

    def _handle_memory_resource(self, uri: str) -> Tuple[str, str]:
        """Handle buffy://memory or buffy://memory/{level]/{key]."""
        from scripts_01.memory_engine import MemoryLevel
        parts = uri.replace("buffy://memory", "").strip("/").split("/", 1)
        me = self._get_memory_engine()

        if not parts or parts[0] == "":
            # Overview: list all levels with counts
            overview = {}
            for level in MemoryLevel:
                entries = me.list_entries(level)
                overview[level.value] = len(entries)
            return json.dumps(overview, ensure_ascii=False, indent=2), "application/json"
        elif len(parts) >= 2:
            level_str, key = parts[0], parts[1]
            try:
                level = MemoryLevel(level_str)
            except ValueError:
                return "", f"Invalid memory level: {level_str}"
            entry = me.retrieve(level, key)
            if entry is None:
                return "", f"Memory entry not found: {level}/{key}"
            return entry.content, "text/markdown"
        else:
            # buffy://memory/{level} — list entries at level
            level_str = parts[0]
            try:
                level = MemoryLevel(level_str)
            except ValueError:
                return "", f"Invalid memory level: {level_str}"
            entries = me.list_entries(level)
            data = [{"key": e.key, "summary": e.summary[:100]} for e in entries]
            return json.dumps(data, ensure_ascii=False, indent=2), "application/json"

    # ── Prompt registration ────────────────────────────────

    def _register_prompts(self) -> None:
        """Регистрирует MCP prompts."""
        self._prompts["context_resume"] = McpPrompt(
            name="context_resume",
            description="Restore Buffy's context from the last session. Returns a prompt for starting a new session with previous context.",
            arguments=[],
            handler=self._handle_prompt_context_resume,
        )

        self._prompts["knowledge_search"] = McpPrompt(
            name="knowledge_search",
            description="Search the Knowledge Engine and format results as a context prompt.",
            arguments=[
                {"name": "query", "description": "Search query", "required": True},
                {"name": "mode", "description": "Search mode: keyword, semantic, hybrid", "default": "hybrid"},
            ],
            handler=self._handle_prompt_knowledge_search,
        )

        self._prompts["task_start"] = McpPrompt(
            name="task_start",
            description="Start a new task with context. Returns a structured prompt for beginning work on a task.",
            arguments=[
                {"name": "task", "description": "Task description", "required": True},
                {"name": "project", "description": "Project name", "default": "freebuff"},
            ],
            handler=self._handle_prompt_task_start,
        )

    def _handle_prompt_context_resume(self, args: Dict[str, Any]) -> str:
        """Generate context resume prompt."""
        conspect = self._handle_context_resume({})["data"] or ""
        return (
            "I am starting a new session. Here is the context from my previous session:\n\n"
            f"{conspect}\n\n"
            "Please read BUFFY.md, restore context, and briefly tell me "
            "what was done in the previous session and what we are continuing."
        )

    def _handle_prompt_knowledge_search(self, args: Dict[str, Any]) -> str:
        """Generate knowledge search prompt."""
        query = args.get("query", "")
        mode = args.get("mode", "hybrid")
        result = self._handle_knowledge_search({"query": query, "mode": mode})
        results = result.get("data", [])
        lines = [f"## Knowledge Search Results for: '{query}'", ""]
        for r in results:
            lines.append(f"### [{r.get('score', 0):.3f}] {r.get('doc_id', '?')}")
            lines.append(r.get("snippet", "")[:300])
            lines.append("")
        return "\n".join(lines) if lines else "No results found."

    def _handle_prompt_task_start(self, args: Dict[str, Any]) -> str:
        """Generate task start prompt."""
        task = args.get("task", "")
        project = args.get("project", "freebuff")
        return (
            f"TASK: {task}\n"
            f"PROJECT: {project}\n\n"
            "Please:\n"
            "1. Read BUFFY.md and relevant docs\n"
            "2. Create a plan with TODO steps\n"
            "3. Implement the changes\n"
            "4. Run tests and code review\n"
            "5. Document changes in CHANGELOG.md"
        )

    # ── Tool handlers ──────────────────────────────────────

    def _handle_knowledge_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search Knowledge Engine."""
        query = arguments.get("query", "")
        mode = arguments.get("mode", "hybrid")
        top_k = arguments.get("top_k", 10)

        if not query:
            return {"success": False, "error": "query is required"}

        try:
            ke = self._get_knowledge_engine()
            results = ke.search(query, top_k=top_k, mode=mode)
            self._publish("knowledge.searched", {"query": query, "results": len(results)})
            return {
                "success": True,
                "data": [
                    {
                        "doc_id": r.doc_id,
                        "score": r.score,
                        "snippet": r.snippet,
                        "metadata": r.metadata,
                    }
                    for r in results
                ],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_memory_store(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Store memory entry."""
        from scripts_01.memory_engine import MemoryEngine, MemoryLevel, ContentType

        level_str = arguments.get("level", "")
        key = arguments.get("key", "")
        content = arguments.get("content", "")
        summary = arguments.get("summary", "")

        if not all([level_str, key, content]):
            return {"success": False, "error": "level, key, content are required"}

        try:
            level = MemoryLevel(level_str)
        except ValueError:
            return {"success": False, "error": f"Invalid level: {level_str}"}

        try:
            me = self._get_memory_engine()
            me.store(
                level=level,
                key=key,
                content=content,
                content_type=ContentType.TEXT,
                summary=summary,
            )
            self._publish("memory.stored", {"level": level_str, "key": key})
            return {"success": True, "data": f"Stored {level_str}/{key}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_memory_retrieve(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve memory entry."""
        from scripts_01.memory_engine import MemoryLevel

        level_str = arguments.get("level", "")
        key = arguments.get("key", "")

        if not all([level_str, key]):
            return {"success": False, "error": "level and key are required"}

        try:
            level = MemoryLevel(level_str)
        except ValueError:
            return {"success": False, "error": f"Invalid level: {level_str}"}

        try:
            me = self._get_memory_engine()
            entry = me.retrieve(level, key)
            if entry is None:
                return {"success": False, "error": f"Not found: {level_str}/{key}"}
            return {
                "success": True,
                "data": {
                    "key": entry.key,
                    "content": entry.content,
                    "summary": entry.summary,
                    "content_type": entry.content_type.value if hasattr(entry.content_type, 'value') else str(entry.content_type),
                    "metadata": entry.metadata,
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_memory_list(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List memory entries at a level."""
        from scripts_01.memory_engine import MemoryLevel

        level_str = arguments.get("level", "")
        if not level_str:
            return {"success": False, "error": "level is required"}

        try:
            level = MemoryLevel(level_str)
        except ValueError:
            return {"success": False, "error": f"Invalid level: {level_str}"}

        try:
            me = self._get_memory_engine()
            entries = me.list_entries(level)
            return {
                "success": True,
                "data": [
                    {
                        "key": e.key,
                        "summary": e.summary[:100],
                        "content_type": e.content_type.value if hasattr(e.content_type, 'value') else str(e.content_type),
                    }
                    for e in entries
                ],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_session_status(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get session status."""
        try:
            cm = self._get_context_manager()
            from scripts_01.context_manager import SessionStatus
            active = cm.list_sessions(SessionStatus.ACTIVE)
            if active:
                s = active[0]
                status = cm.get_context_status(s["session_id"])
                return {"success": True, "data": {"session": s, "context": status}}
            else:
                return {"success": True, "data": {"session": None, "message": "No active sessions"}}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_context_resume(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get last conspect for context restoration."""
        summaries_dir = self.workspace / "context_12" / "summaries"
        if not summaries_dir.is_dir():
            return {"success": True, "data": ""}

        files = sorted(
            [f for f in summaries_dir.iterdir() if f.name.endswith(".md")],
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        if not files:
            return {"success": True, "data": ""}

        try:
            content = files[0].read_text(encoding="utf-8")
            return {"success": True, "data": content, "metadata": {"file": files[0].name}}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_plugins_list(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List loaded plugins."""
        try:
            from scripts_01.plugin_api import PluginRegistry, PluginLoader
            registry = PluginRegistry()
            loader = PluginLoader(registry)
            loader.load_all()
            state = registry.get_state()
            return {"success": True, "data": state}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Bridge Layer handlers ──────────────────────────────

    def _handle_bridge_connect(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Connect to an external MCP server."""
        bridge = self._get_bridge_layer()
        if bridge is None:
            return {"success": False, "error": "BridgeLayer not available"}

        transport = arguments.get("transport", "")
        name = arguments.get("name")

        try:
            if transport == "stdio":
                command = arguments.get("command", "")
                args_str = arguments.get("args", "")
                args_list = args_str.split() if args_str else []

                if not command:
                    return {"success": False, "error": "command is required for stdio transport"}

                result = bridge.connect_mcp_stdio(
                    command=command,
                    args=args_list,
                    cwd=str(self.workspace),
                    name=name,
                )
                self._publish("bridge.connected", {"transport": "stdio", "server": result.get("server", command), "tools": result.get("tools", 0)})
                return result

            elif transport == "http":
                endpoint = arguments.get("endpoint", "")
                if not endpoint:
                    return {"success": False, "error": "endpoint is required for http transport"}

                result = bridge.connect_mcp_http(
                    endpoint=endpoint,
                    name=name,
                )
                self._publish("bridge.connected", {"transport": "http", "server": result.get("server", endpoint), "tools": result.get("tools", 0)})
                return result

            else:
                return {"success": False, "error": f"Unknown transport: {transport}. Use 'stdio' or 'http'."}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_bridge_list(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List connected MCP servers."""
        bridge = self._get_bridge_layer()
        if bridge is None:
            return {"success": False, "error": "BridgeLayer not available"}

        servers = bridge.list_mcp_servers()
        return {
            "success": True,
            "data": {
                "servers": servers,
                "total": len(servers),
            },
        }

    def _handle_bridge_disconnect(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Disconnect an MCP server."""
        bridge = self._get_bridge_layer()
        if bridge is None:
            return {"success": False, "error": "BridgeLayer not available"}

        name = arguments.get("name", "")
        if not name:
            return {"success": False, "error": "name is required"}

        ok = bridge.disconnect_mcp(name)
        self._publish("bridge.disconnected", {"server": name, "success": ok})
        return {
            "success": ok,
            "data": {"disconnected": ok, "server": name},
            "error": None if ok else f"Server not found: {name}",
        }

    def _handle_bridge_rpc(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Send JSON-RPC to a connected MCP server."""
        bridge = self._get_bridge_layer()
        if bridge is None:
            return {"success": False, "error": "BridgeLayer not available"}

        server_name = arguments.get("server", "")
        method = arguments.get("method", "")

        if not server_name:
            return {"success": False, "error": "server is required"}
        if not method:
            return {"success": False, "error": "method is required"}

        # Build params based on method
        if method == "tools/call":
            tool = arguments.get("tool", "")
            args_str = arguments.get("arguments", "{)")
            try:
                args_dict = json.loads(args_str)
            except json.JSONDecodeError:
                args_dict = {}

            params = {"name": tool, "arguments": args_dict}
        else:
            params = {}

        result = bridge._rpc_to_server(server_name, method, params)
        self._publish("bridge.rpc", {"server": server_name, "method": method, "success": result.get("success", False)})
        return result

    # ── Bootstrap Engine handlers ──────────────────────────

    def _handle_bootstrap_check(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Check environment state via Bootstrap Engine."""
        engine = self._get_bootstrap_engine()
        if engine is None:
            return {"success": False, "error": "BootstrapEngine not available"}

        try:
            quick = arguments.get("quick", False)
            if quick:
                env = engine._checker.check_quick()
            else:
                env = engine.check()

            self._publish("bootstrap.checked", {"quick": quick, "os": env.os_type})

            return {
                "success": True,
                "data": {
                    "os": env.os_type,
                    "is_termux": env.is_termux,
                    "python_version": env.python_version,
                    "node_version": env.node_version,
                    "git_available": env.git_available,
                    "disk_free_gb": env.disk_free_gb,
                    "ram_total_mb": env.ram_total_mb,
                    "ram_available_mb": env.ram_available_mb,
                    "pip_packages": len(env.pip_packages),
                    "has_git": env.has_git,
                    "has_env_file": env.has_env_file,
                    "workspace": env.workspace,
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_bootstrap_run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Run full bootstrap cycle."""
        profile = arguments.get("profile", "minimal")

        try:
            from freebuff_plugin_03 import BootstrapEngine
            bus = self._get_event_bus()
            engine = BootstrapEngine(
                workspace_root=str(self.workspace),
                profile=profile,
                event_bus=bus or None,
            )
            report = engine.run()

            self._publish("bootstrap.ran", {
                "profile": profile,
                "success": report.success,
                "duration_ms": report.duration_ms,
                "steps": len(report.steps),
            })

            return {
                "success": report.success,
                "data": {
                    "profile": report.profile,
                    "duration_ms": report.duration_ms,
                    "steps": [
                        {
                            "name": s.name,
                            "status": s.status,
                            "duration_ms": s.duration_ms,
                            "error": s.error,
                        }
                        for s in report.steps
                    ],
                    "warnings": report.warnings[:10],
                    "errors": report.errors[:10],
                    "diagnosis": {
                        "health_score": report.diagnosis.health_score if report.diagnosis else None,
                        "path_issues": report.diagnosis.path_issues if report.diagnosis else [],
                        "runtime_issues": report.diagnosis.runtime_issues if report.diagnosis else [],
                        "dependency_issues": report.diagnosis.dependency_issues if report.diagnosis else [],
                        "key_issues": report.diagnosis.key_issues if report.diagnosis else [],
                    } if report.diagnosis else None,
                    "environment": {
                        "os": report.environment.os_type if report.environment else "unknown",
                        "python": report.environment.python_version if report.environment else "",
                        "git": report.environment.git_available if report.environment else False,
                    } if report.environment else None,
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_bootstrap_status(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get bootstrap status."""
        engine = self._get_bootstrap_engine()
        if engine is None:
            return {"success": False, "error": "BootstrapEngine not available"}

        try:
            status = engine.get_status()
            return {
                "success": True,
                "data": status,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Runtime Abstraction Layer handlers ─────────────────

    def _handle_runtime_list(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List discovered runtimes and active runtime."""
        registry = self._get_runtime_registry()
        if registry is None:
            return {"success": False, "error": "RuntimeRegistry not available"}

        try:
            status = registry.get_status()
            self._publish("runtime.listed", {"total": status.get("total", 0), "active": status.get("active")})
            return {"success": True, "data": status}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_runtime_connect(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Connect to a runtime by name."""
        registry = self._get_runtime_registry()
        if registry is None:
            return {"success": False, "error": "RuntimeRegistry not available"}

        name = arguments.get("name", "")
        if not name:
            return {"success": False, "error": "name is required"}

        try:
            ok, msg = registry.connect(name)
            self._publish("runtime.connected", {"runtime": name, "success": ok, "message": msg})
            return {"success": ok, "data": {"runtime": name, "connected": ok, "message": msg}}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_runtime_disconnect(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Disconnect a runtime by name."""
        registry = self._get_runtime_registry()
        if registry is None:
            return {"success": False, "error": "RuntimeRegistry not available"}

        name = arguments.get("name", "")
        if not name:
            return {"success": False, "error": "name is required"}

        try:
            ok = registry.disconnect(name)
            self._publish("runtime.disconnected", {"runtime": name, "success": ok})
            return {"success": ok, "data": {"runtime": name, "disconnected": ok}}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_runtime_select(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Set active runtime by name."""
        registry = self._get_runtime_registry()
        if registry is None:
            return {"success": False, "error": "RuntimeRegistry not available"}

        name = arguments.get("name", "")
        if not name:
            return {"success": False, "error": "name is required"}

        try:
            ok = registry.set_active(name)
            if not ok:
                return {"success": False, "error": f"Runtime not registered: {name}"}
            self._publish("runtime.selected", {"runtime": name})
            return {"success": True, "data": {"runtime": name, "active": True}}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_runtime_generate(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a response from a runtime."""
        registry = self._get_runtime_registry()
        if registry is None:
            return {"success": False, "error": "RuntimeRegistry not available"}

        capability = arguments.get("capability")
        explicit_name = arguments.get("name")
        prompt = arguments.get("prompt", "")
        messages = arguments.get("messages")
        system = arguments.get("system")
        try:
            temperature = float(arguments.get("temperature", 0.7))
        except (TypeError, ValueError):
            return {"success": False, "error": "temperature must be a number"}
        max_tokens = arguments.get("max_tokens")
        if max_tokens is not None:
            try:
                max_tokens = int(max_tokens)
                if max_tokens <= 0:
                    return {"success": False, "error": "max_tokens must be positive"}
            except (TypeError, ValueError):
                return {"success": False, "error": "max_tokens must be an integer"}

        # Build and validate messages list
        if messages is None:
            if not prompt:
                return {"success": False, "error": "prompt or messages is required"}
            messages = [{"role": "user", "content": prompt}]
        elif not isinstance(messages, list) or not all(
            isinstance(m, dict) and "role" in m and "content" in m for m in messages
        ):
            return {"success": False, "error": "messages must be a list of dicts with role and content"}

        # Determine target runtime
        runtime_name = None
        if explicit_name:
            runtime_name = explicit_name
        elif capability:
            policy_engine = self._get_policy_engine()
            if policy_engine is not None:
                runtime_name = policy_engine.select_runtime(capability)
            if runtime_name is None:
                cap_reg = self._runtime_capability_registry
                if cap_reg is None:
                    return {"success": False, "error": "RuntimeCapabilityRegistry not available"}
                best = cap_reg.get_runtime_for_capability(capability)
                if best is None:
                    return {"success": False, "error": f"No runtime available for capability: {capability}"}
                runtime_name = best["runtime"]
            if registry.get(runtime_name) is None:
                return {"success": False, "error": f"Runtime selected for capability is not registered: {runtime_name}"}
        else:
            active = registry.get_active()
            if active is None:
                return {"success": False, "error": "No active runtime. Use runtime_select or provide name/capability."}
            runtime_name = active.name

        if not runtime_name or not isinstance(runtime_name, str):
            return {"success": False, "error": "Could not determine target runtime"}

        # Ensure connected
        adapter = registry.get_adapter(runtime_name)
        if adapter is None or not adapter.is_connected():
            ok, msg = registry.connect(runtime_name)
            if not ok:
                return {"success": False, "error": f"Could not connect to runtime {runtime_name}: {msg}"}
            adapter = registry.get_adapter(runtime_name)
            if adapter is None:
                return {"success": False, "error": f"Runtime adapter unavailable after connect: {runtime_name}"}

        try:
            result = adapter.generate(
                messages=messages,
                system=system,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            self._publish("runtime.generated", {
                "runtime": runtime_name,
                "success": result.error is None,
                "model_used": result.model_used,
            })
            if result.error:
                return {"success": False, "error": result.error, "data": {"runtime": runtime_name}}
            return {
                "success": True,
                "data": {
                    "runtime": runtime_name,
                    "content": result.content,
                    "model_used": result.model_used,
                    "provider_used": result.provider_used,
                    "latency_ms": result.latency_ms,
                    "usage": result.usage,
                    "finish_reason": result.finish_reason,
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e), "data": {"runtime": runtime_name}}

    def _handle_policy_override(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Применить диалоговое переопределение «используй X вместо Y» (правило 11).

        Распознаёт естественно-языковую фразу и назначает Runtime на capability
        через PolicyEngine.set_preference (persist в policies.json).
        """
        message = arguments.get("message", "")
        if not message or not isinstance(message, str):
            return {"success": False, "error": "message is required"}

        policy_engine = self._get_policy_engine()
        if policy_engine is None:
            return {
                "success": False,
                "error": "PolicyEngine not available — override not applied",
            }

        try:
            from freebuff_plugin_03.policy import apply_override
            result = apply_override(message, policy_engine)
        except Exception as e:
            return {"success": False, "error": f"Policy override failed: {e}"}

        if result is None:
            return {
                "success": False,
                "error": (
                    "Could not parse override intent from message. "
                    "Examples: \"use deepseek instead of claude for coding\", "
                    "\"используй freebuff для research\""
                ),
            }

        self._publish("policy.override", {
            "capability": result.get("capability"),
            "runtime": result.get("runtime"),
            "previous_runtime": result.get("previous_runtime"),
            "applied": result.get("applied", True),
        })

        return {"success": True, "data": result}

    # ── MCP protocol handlers ──────────────────────────────

    def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request."""
        self._client_info = params.get("clientInfo", {})
        self._initialized = True

        self._publish("server.initialized", {
            "client": self._client_info.get("name", "unknown"),
            "protocol_version": PROTOCOL_VERSION,
        })

        return {
            "protocolVersion": PROTOCOL_VERSION,
            "serverInfo": {
                "name": SERVER_NAME,
                "version": SERVER_VERSION,
            },
            "capabilities": {
                "tools": {"listChanged": True},
                "resources": {"listChanged": True, "subscribe": False},
                "prompts": {"listChanged": True},
            },
        }

    def handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request."""
        tools = []
        for name, tool in sorted(self._tools.items()):
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema,
            })
        return {"tools": tools}

    def handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request."""
        name = params.get("name", "")
        arguments = params.get("arguments", {})

        tool = self._tools.get(name)
        if tool is None:
            raise ValueError(f"Unknown tool: {name}")

        if tool.handler is None:
            raise ValueError(f"Tool has no handler: {name}")

        try:
            result = tool.handler(arguments)
        except Exception as e:
            # Tool handler raised — return MCP tool error (not protocol error)
            return {
                "content": [{"type": "text", "text": json.dumps(
                    {"success": False, "error": str(e)}, ensure_ascii=False,
                )}],
                "isError": True,
            }

        # MCP expects content array with TextContent
        if isinstance(result, dict):
            content_text = json.dumps(result, ensure_ascii=False, indent=2)
        else:
            content_text = str(result)

        return {
            "content": [{"type": "text", "text": content_text}],
            "isError": isinstance(result, dict) and not result.get("success", True),
        }

    def handle_resources_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/list request."""
        resources = []
        for uri, res in sorted(self._resources.items()):
            resources.append({
                "uri": res.uri,
                "name": res.name,
                "description": res.description,
                "mimeType": res.mime_type,
            })
        return {"resources": resources}

    def handle_resources_read(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/read request."""
        uri = params.get("uri", "")
        res = self._resources.get(uri)

        if res is None:
            # Try pattern matching for dynamic URIs
            if uri.startswith("buffy://knowledge/"):
                res = self._resources.get("buffy://knowledge")
            elif uri.startswith("buffy://memory/"):
                res = self._resources.get("buffy://memory")

        if res is None or res.handler is None:
            raise ValueError(f"Unknown resource: {uri}")

        content, mime_type = res.handler(uri)
        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": mime_type,
                    "text": content,
                }
            ]
        }

    def handle_prompts_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompts/list request."""
        prompts = []
        for name, p in sorted(self._prompts.items()):
            prompts.append({
                "name": p.name,
                "description": p.description,
                "arguments": p.arguments,
            })
        return {"prompts": prompts}

    def handle_prompts_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompts/get request."""
        name = params.get("name", "")
        arguments = params.get("arguments", {})

        prompt = self._prompts.get(name)
        if prompt is None:
            raise ValueError(f"Unknown prompt: {name}")

        if prompt.handler:
            text = prompt.handler(arguments)
        else:
            text = prompt.description

        return {
            "description": prompt.description,
            "messages": [
                {
                    "role": "user",
                    "content": {"type": "text", "text": text},
                }
            ],
        }

    # ── JSON-RPC message dispatch ──────────────────────────

    def dispatch(self, message: Dict[str, Any]) -> Optional[str]:
        """Dispatch a JSON-RPC message and return response (or None for notifications).

        Args:
            message: parsed JSON-RPC message

        Returns:
            JSON response string, or None for notifications
        """
        req_id = message.get("id")
        method = message.get("method", "")
        params = message.get("params", {})

        # Notifications (no id) — don't send response
        is_notification = req_id is None

        try:
            if method == "initialize":
                result = self.handle_initialize(params)
                return rpc_response(req_id, result) if not is_notification else None

            elif method == "notifications/initialized":
                # Client signals readiness — no response needed
                return None

            elif method == "ping":
                return rpc_response(req_id, {}) if not is_notification else None

            elif method == "tools/list":
                result = self.handle_tools_list(params)
                return rpc_response(req_id, result) if not is_notification else None

            elif method == "tools/call":
                result = self.handle_tools_call(params)
                return rpc_response(req_id, result) if not is_notification else None

            elif method == "resources/list":
                result = self.handle_resources_list(params)
                return rpc_response(req_id, result) if not is_notification else None

            elif method == "resources/read":
                result = self.handle_resources_read(params)
                return rpc_response(req_id, result) if not is_notification else None

            elif method == "resources/templates/list":
                # Return empty list (no URI templates for now)
                return rpc_response(req_id, {"resourceTemplates": []}) if not is_notification else None

            elif method == "prompts/list":
                result = self.handle_prompts_list(params)
                return rpc_response(req_id, result) if not is_notification else None

            elif method == "prompts/get":
                result = self.handle_prompts_get(params)
                return rpc_response(req_id, result) if not is_notification else None

            elif method == "logging/setLevel":
                # Accept any log level, no response data needed
                return rpc_response(req_id, {}) if not is_notification else None

            elif method == "shutdown":
                # MCP shutdown — signal readiness to stop (no actual exit here)
                self._publish("server.shutdown", {})
                return rpc_response(req_id, {}) if not is_notification else None

            else:
                if is_notification:
                    return None
                return rpc_error(req_id, METHOD_NOT_FOUND, f"Method not found: {method}")

        except ValueError as e:
            if is_notification:
                return None
            return rpc_error(req_id, INVALID_PARAMS, str(e))
        except Exception as e:
            if is_notification:
                return None
            trace = traceback.format_exc()[:500]
            return rpc_error(req_id, INTERNAL_ERROR, str(e), {"trace": trace})

    # ── stdio transport ─────────────────────────────────────

    async def run_stdio(self) -> None:
        """Run MCP server over stdio transport.

        Reads JSON-RPC messages from stdin (one per line),
        writes responses to stdout.
        """
        # Ensure stdout is line-buffered
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(line_buffering=True)

        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

        while True:
            try:
                line = await reader.readline()
                if not line:
                    break  # EOF

                line_str = line.decode("utf-8").strip()
                if not line_str:
                    continue

                # Parse JSON-RPC message
                try:
                    message = json.loads(line_str)
                except json.JSONDecodeError as e:
                    # Send parse error
                    sys.stdout.write(rpc_error(None, PARSE_ERROR, f"Parse error: {e}") + "\n")
                    sys.stdout.flush()
                    continue

                # Handle batch requests
                if isinstance(message, list):
                    responses = []
                    for msg in message:
                        resp = self.dispatch(msg)
                        if resp:
                            responses.append(json.loads(resp))
                    if responses:
                        sys.stdout.write(json.dumps(responses, ensure_ascii=False) + "\n")
                        sys.stdout.flush()
                    continue

                # Single request
                response = self.dispatch(message)
                if response:
                    sys.stdout.write(response + "\n")
                    sys.stdout.flush()

            except Exception as e:
                print(f"⚠️ MCP server error: {e}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)

    def run_sync(self) -> None:
        """Run MCP server synchronously (blocking, line-by-line stdin)."""
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(line_buffering=True)

        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            try:
                message = json.loads(line)
            except json.JSONDecodeError as e:
                sys.stdout.write(rpc_error(None, PARSE_ERROR, f"Parse error: {e}") + "\n")
                sys.stdout.flush()
                continue

            # Batch request
            if isinstance(message, list):
                responses = []
                for msg in message:
                    resp = self.dispatch(msg)
                    if resp:
                        responses.append(json.loads(resp))
                if responses:
                    sys.stdout.write(json.dumps(responses, ensure_ascii=False) + "\n")
                    sys.stdout.flush()
                continue

            response = self.dispatch(message)
            if response:
                sys.stdout.write(response + "\n")
                sys.stdout.flush()

    # ── Status / introspection ─────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Return server status for CLI."""
        return {
            "server": SERVER_NAME,
            "version": SERVER_VERSION,
            "protocol": PROTOCOL_VERSION,
            "workspace": str(self.workspace),
            "initialized": self._initialized,
            "tools": len(self._tools),
            "resources": len(self._resources),
            "prompts": len(self._prompts),
            "tool_names": sorted(self._tools.keys()),
            "resource_uris": sorted(self._resources.keys()),
            "prompt_names": sorted(self._prompts.keys()),
        }

    def list_tools_info(self) -> List[Dict[str, Any]]:
        """List all tools with full info (for CLI)."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "input_schema": t.input_schema,
            }
            for t in sorted(self._tools.values(), key=lambda x: x.name)
        ]

    def list_resources_info(self) -> List[Dict[str, Any]]:
        """List all resources with full info (for CLI)."""
        return [
            {
                "uri": r.uri,
                "name": r.name,
                "description": r.description,
                "mime_type": r.mime_type,
            }
            for r in sorted(self._resources.values(), key=lambda x: x.uri)
        ]

    # ── Streamable HTTP transport ──────────────────────────

    def run_http(self, host: str = "127.0.0.1", port: int = 8765) -> None:
        """Run MCP server over Streamable HTTP transport.

        Single endpoint /mcp:
        - POST: JSON-RPC requests (application/json response)
        - GET: SSE notification stream (text/event-stream)
        - DELETE: session termination (204 No Content)

        Session management via Mcp-Session-Id header.
        Spec: MCP 2025-03-26 Streamable HTTP transport.
        """
        session_manager = McpSessionManager()
        httpd = McpHttpServer(
            (host, port),
            McpHTTPRequestHandler,
            self,
            session_manager,
        )
        print(f"🌐 MCP HTTP Server: http://{host}:{port}/mcp", file=sys.stderr)
        print(f"   Protocol: {PROTOCOL_VERSION}", file=sys.stderr)
        print(f"   Tools: {len(self._tools)} | Resources: {len(self._resources)} | Prompts: {len(self._prompts)}", file=sys.stderr)
        print(f"   Press Ctrl+C to stop", file=sys.stderr)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...", file=sys.stderr)
        finally:
            httpd.shutdown()


# ═══════════════════════════════════════════════════════════════
# Streamable HTTP Transport (MCP 2025-03-26)
# ═══════════════════════════════════════════════════════════════


class McpHttpServer(ThreadingHTTPServer):
    """ThreadingHTTPServer with BuffyMcpServer and session manager."""

    daemon_threads = True

    def __init__(self, server_addr, handler_class,
                 mcp_server: "BuffyMcpServer",
                 session_manager: McpSessionManager):
        super().__init__(server_addr, handler_class)
        self.mcp_server = mcp_server
        self.session_manager = session_manager


class McpHTTPRequestHandler(BaseHTTPRequestHandler):
    """HTTP handler for MCP Streamable HTTP transport.

    Single endpoint /mcp:
    - POST: JSON-RPC requests → application/json, or 202 for notifications
    - GET: SSE stream (text/event-stream) for server-to-client notifications
    - DELETE: session termination (204 No Content)

    Session management via Mcp-Session-Id header (assigned on initialize).
    Mcp-Protocol-Version header included in all responses.
    """

    server_version = "BuffyMCP/1.0"
    protocol_version = "HTTP/1.1"  # needed for keep-alive / SSE

    @property
    def _mcp(self) -> "BuffyMcpServer":
        return self.server.mcp_server

    @property
    def _sessions(self) -> McpSessionManager:
        return self.server.session_manager

    # ── Response helpers ───────────────────────────────────

    def _send_json(self, status: int, body: str,
                   extra_headers: Optional[Dict[str, str]] = None) -> None:
        """Send a JSON HTTP response."""
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Mcp-Protocol-Version", PROTOCOL_VERSION)
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _send_status(self, status: int,
                     extra_headers: Optional[Dict[str, str]] = None) -> None:
        """Send a status-only response (no body).

        Per RFC 7230 §3.3.2, 204 responses MUST NOT include Content-Length.
        """
        self.send_response(status)
        if status != 204:
            self.send_header("Content-Length", "0")
        self.send_header("Mcp-Protocol-Version", PROTOCOL_VERSION)
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()

    def _send_error_json(self, status: int, code: int, message: str) -> None:
        """Send an HTTP error with JSON-RPC error body."""
        self._send_json(status, rpc_error(None, code, message))

    def _validate_origin(self) -> bool:
        """Validate Origin header to prevent DNS rebinding attacks.

        Per MCP 2025-03-26 spec, servers MUST validate the Origin header.
        Allows: no Origin (non-browser clients), localhost, 127.0.0.1.
        Uses urlparse to prevent bypass via e.g. http://localhost.evil.com.
        """
        from urllib.parse import urlparse

        origin = self.headers.get("Origin")
        if origin is None:
            return True  # Non-browser clients (curl, CLI) don't send Origin
        try:
            parsed = urlparse(origin)
            return parsed.hostname in ("localhost", "127.0.0.1", "0.0.0.0")
        except Exception:
            return False

    # ── POST: JSON-RPC requests ────────────────────────────

    def do_POST(self) -> None:
        if self.path != "/mcp":
            self._send_error_json(404, INVALID_REQUEST, f"Unknown path: {self.path}")
            return

        if not self._validate_origin():
            self._send_error_json(403, INVALID_REQUEST, "Invalid Origin header")
            return

        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length) if content_length > 0 else b""

        try:
            message = json.loads(raw_body)
        except json.JSONDecodeError as e:
            self._send_error_json(400, PARSE_ERROR, f"Parse error: {e}")
            return

        # initialize → create new session, return Mcp-Session-Id
        if isinstance(message, dict) and message.get("method") == "initialize":
            session_id = self._sessions.create_session()
            response = self._mcp.dispatch(message)
            if response:
                self._send_json(200, response, {"Mcp-Session-Id": session_id})
            else:
                self._send_status(202, {"Mcp-Session-Id": session_id})
            return

        # Non-initialize POSTs require valid Mcp-Session-Id
        session_id = self.headers.get("Mcp-Session-Id")
        if session_id and not self._sessions.get_session(session_id):
            self._send_error_json(404, INVALID_REQUEST, "Session not found")
            return

        # Batch request
        if isinstance(message, list):
            responses = []
            for msg in message:
                resp = self._mcp.dispatch(msg)
                if resp:
                    responses.append(json.loads(resp))
            if responses:
                self._send_json(200, json.dumps(responses, ensure_ascii=False))
            else:
                self._send_status(202)
            return

        # Single message
        is_notification = message.get("id") is None
        response = self._mcp.dispatch(message)

        if is_notification or response is None:
            self._send_status(202)
        else:
            self._send_json(200, response)

    # ── GET: SSE notification stream ────────────────────────

    def do_GET(self) -> None:
        if self.path != "/mcp":
            self._send_error_json(404, INVALID_REQUEST, f"Unknown path: {self.path}")
            return

        if not self._validate_origin():
            self._send_error_json(403, INVALID_REQUEST, "Invalid Origin header")
            return

        session_id = self.headers.get("Mcp-Session-Id")
        if not session_id:
            self._send_error_json(400, INVALID_REQUEST, "Mcp-Session-Id required for GET")
            return

        session = self._sessions.get_session(session_id)
        if not session:
            self._send_error_json(404, INVALID_REQUEST, "Session not found")
            return

        # Open SSE stream
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Mcp-Protocol-Version", PROTOCOL_VERSION)
        self.end_headers()

        try:
            while session.active:
                try:
                    msg = session.notification_queue.get(timeout=30)
                    self.wfile.write(f"data: {msg}\n\n".encode("utf-8"))
                    self.wfile.flush()
                except Empty:
                    # Heartbeat to keep connection alive
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass  # Client disconnected

    # ── DELETE: session termination ─────────────────────────

    def do_DELETE(self) -> None:
        if self.path != "/mcp":
            self._send_error_json(404, INVALID_REQUEST, f"Unknown path: {self.path}")
            return

        if not self._validate_origin():
            self._send_error_json(403, INVALID_REQUEST, "Invalid Origin header")
            return

        session_id = self.headers.get("Mcp-Session-Id")
        if not session_id:
            self._send_error_json(400, INVALID_REQUEST, "Mcp-Session-Id required")
            return

        if self._sessions.delete_session(session_id):
            self._send_status(204)
        else:
            self._send_error_json(404, INVALID_REQUEST, "Session not found")

    def log_message(self, format: str, *args) -> None:
        """Suppress default logging."""
        pass


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="MCP Server для Buffy Project — Model Context Protocol (stdio + Streamable HTTP)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Claude integration (claude_desktop_config.json) — stdio:
  {
    "mcpServers": {
      "buffy": {
        "command": "python",
        "args": ["scripts_01/mcp_server.py"]
      }
    }
  }

HTTP integration (Streamable HTTP transport):
  python scripts_01/mcp_server.py --http --port 8765
  Endpoint: http://127.0.0.1:8765/mcp
  POST: JSON-RPC, GET: SSE stream, DELETE: session

Examples:
  python scripts_01/mcp_server.py                  # stdio MCP server
  python scripts_01/mcp_server.py --http           # HTTP MCP server (port 8765)
  python scripts_01/mcp_server.py --status         # server status
  python scripts_01/mcp_server.py --tools          # list MCP tools
  python scripts_01/mcp_server.py --resources      # list MCP resources
  python scripts_01/mcp_server.py --call knowledge_search '{"query": "router"]'
        """,
    )
    parser.add_argument("--status", action="store_true", help="Show server status")
    parser.add_argument("--tools", action="store_true", help="List all MCP tools")
    parser.add_argument("--resources", action="store_true", help="List all MCP resources")
    parser.add_argument("--prompts", action="store_true", help="List all MCP prompts")
    parser.add_argument("--call", nargs=2, metavar=("TOOL", "ARGS"), help="Call a tool directly")
    parser.add_argument("--read", metavar="URI", help="Read a resource directly")
    parser.add_argument("--async-mode", dest="async_mode", action="store_true", help="Use async stdio transport")
    parser.add_argument("--http", action="store_true", help="Run Streamable HTTP server (POST/GET/DELETE at /mcp)")
    parser.add_argument("--fastapi", action="store_true", help="Run FastAPI server (requires fastapi+uvicorn)")
    parser.add_argument("--tunnel", action="store_true", help="Start Cloudflare Tunnel (requires --fastapi)")
    parser.add_argument("--host", default="127.0.0.1", help="HTTP server host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="HTTP server port (default: 8765)")

    args = parser.parse_args()

    server = BuffyMcpServer()

    if args.status:
        status = server.get_status()
        print(f"📊 MCP SERVER STATUS")
        print(f"   Server:     {status['server']} v{status['version']}")
        print(f"   Protocol:   {status['protocol']}")
        print(f"   Workspace:  {status['workspace']}")
        print(f"   Tools:      {status['tools']}")
        print(f"   Resources:  {status['resources']}")
        print(f"   Prompts:    {status['prompts']}")
        print(f"\n   Tool names: {', '.join(status['tool_names'])}")
        print(f"   Resources:  {', '.join(status['resource_uris'])}")
        print(f"   Prompts:    {', '.join(status['prompt_names'])}")

    elif args.tools:
        tools = server.list_tools_info()
        print(f"🔧 MCP TOOLS ({len(tools)}):")
        for t in tools:
            print(f"\n  {t['name']} [{t['category']}]")
            print(f"    {t['description'][:100]}")
            props = t['input_schema'].get('properties', {})
            required = t['input_schema'].get('required', [])
            for pname, pschema in props.items():
                req = "*" if pname in required else ""
                ptype = pschema.get('type', 'any')
                desc = pschema.get('description', '')[:60]
                print(f"    - {pname}{req} ({ptype}): {desc}")

    elif args.resources:
        resources = server.list_resources_info()
        print(f"📄 MCP RESOURCES ({len(resources)}):")
        for r in resources:
            print(f"\n  {r['uri']}")
            print(f"    {r['name']}: {r['description'][:100]}")
            print(f"    mime: {r['mime_type']}")

    elif args.prompts:
        print(f"💬 MCP PROMPTS ({len(server._prompts)}):")
        for name, p in sorted(server._prompts.items()):
            print(f"\n  {p.name}")
            print(f"    {p.description[:100]}")
            for arg in p.arguments:
                req = "*" if arg.get("required") else ""
                print(f"    - {arg['name']}{req}: {arg.get('description', '')[:60]}")

    elif args.call:
        tool_name, args_str = args.call
        try:
            arguments = json.loads(args_str)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON args: {e}")
            return
        result = server.handle_tools_call({"name": tool_name, "arguments": arguments})
        if result.get("isError"):
            print(f"❌ Tool error")
        else:
            print(f"✅ Tool result")
        for content in result.get("content", []):
            print(content.get("text", ""))

    elif args.read:
        try:
            result = server.handle_resources_read({"uri": args.read})
            for content in result.get("contents", []):
                print(content.get("text", ""))
        except ValueError as e:
            print(f"❌ {e}")

    else:
        # Default: run MCP server
        if args.tunnel and not args.fastapi:
            print("⚠️  --tunnel requires --fastapi", file=sys.stderr)
            sys.exit(1)
        if args.fastapi:
            try:
                from scripts_01.mcp_fastapi import main as fastapi_main
                sys.argv = [sys.argv[0], "--host", args.host, "--port", str(args.port)]
                if args.tunnel:
                    sys.argv.append("--tunnel")
                fastapi_main()
            except ImportError:
                print("❌ FastAPI not installed. Run: pip install fastapi uvicorn", file=sys.stderr)
                sys.exit(1)
        elif args.http:
            server.run_http(host=args.host, port=args.port)
        elif args.async_mode:
            asyncio.run(server.run_stdio())
        else:
            server.run_sync()


if __name__ == "__main__":
    main()
